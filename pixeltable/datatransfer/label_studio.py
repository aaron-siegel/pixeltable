from __future__ import annotations

import itertools
import logging
from pathlib import Path
from typing import Any, Iterator, Optional
from xml.etree import ElementTree

import label_studio_sdk
import more_itertools
from requests.exceptions import HTTPError

import pixeltable.env as env
import pixeltable.exceptions as excs
import pixeltable.type_system as ts
from pixeltable import Table
from pixeltable.datatransfer.remote import Remote

_logger = logging.getLogger('pixeltable')


class LabelStudioProject(Remote):

    ANNOTATIONS_COLUMN = 'annotations'

    def __init__(self, project_id: int):
        self.project_id = project_id
        self.ls_client = env.Env.get().label_studio_client
        self._project: Optional[label_studio_sdk.project.Project] = None

    @property
    def project(self) -> label_studio_sdk.project.Project:
        if self._project is None:
            try:
                self._project = self.ls_client.get_project(self.project_id)
            except HTTPError as exc:
                raise excs.Error(f'Could not locate Label Studio project: {self.project_id} '
                                 '(cannot connect to server or project no longer exists)') from exc
        return self._project

    @property
    def project_params(self) -> dict[str, Any]:
        return self.project.get_params()

    @property
    def project_title(self) -> str:
        return self.project_params['title']

    @classmethod
    def create(cls, title: str, label_config: str, **kwargs) -> LabelStudioProject:
        ls_client = env.Env.get().label_studio_client
        project = ls_client.start_project(title=title, label_config=label_config, **kwargs)
        project_id = project.get_params()['id']
        return LabelStudioProject(project_id)

    def get_push_columns(self) -> dict[str, ts.ColumnType]:
        config: str = self.project.get_params()['label_config']
        return self._parse_project_config(config)

    def get_pull_columns(self) -> dict[str, ts.ColumnType]:
        return {self.ANNOTATIONS_COLUMN: ts.JsonType(nullable=True)}

    def sync(self, t: Table, col_mapping: dict[str, str], push: bool, pull: bool) -> None:
        _logger.info(f'Syncing Label Studio project "{self.project_title}" with table `{t.get_name()}`'
                     f' (push: {push}, pull: {pull}).')
        tasks = list(self._get_all_tasks())
        if pull:
            self._update_table_from_tasks(t, col_mapping, tasks)
        if push:
            self._create_tasks_from_table(t, col_mapping, tasks)

    def _get_all_tasks(self) -> Iterator[dict]:
        page = 1
        unknown_task_count = 0
        while True:
            result = self.project.get_paginated_tasks(page=page, page_size=_PAGE_SIZE)
            if result.get('end_pagination'):
                break
            for task in result['tasks']:
                rowid = task['meta'].get('rowid')
                if rowid is None:
                    unknown_task_count += 1
                else:
                    yield task
            page += 1
        if unknown_task_count > 0:
            _logger.warning(
                f'Skipped {unknown_task_count} unrecognized task(s) when syncing Label Studio project "{self.project_title}".'
            )

    def _update_table_from_tasks(self, t: Table, col_mapping: dict[str, str], tasks: list[dict]) -> None:
        # `col_mapping` is guaranteed to be a one-to-one dict whose values are a superset
        # of `get_pull_columns`
        assert self.ANNOTATIONS_COLUMN in col_mapping.values()
        annotations_column = next(k for k, v in col_mapping.items() if v == self.ANNOTATIONS_COLUMN)
        updates = [
            {
                '_rowid': task['meta']['rowid'],
                # Replace [] by None to indicate no annotations. We do want to sync rows with no annotations,
                # in order to properly handle the scenario where existing annotations have been deleted in
                # Label Studio.
                annotations_column: task[self.ANNOTATIONS_COLUMN] if len(task[self.ANNOTATIONS_COLUMN]) > 0 else None
            }
            for task in tasks
        ]
        if len(updates) > 0:
            _logger.info(
                f'Updating table `{t.get_name()}`, column `{annotations_column}` with {len(updates)} total annotations.'
            )
            t.batch_update(updates)
            annotations_count = sum(len(task[self.ANNOTATIONS_COLUMN]) for task in tasks)
            print(f'Synced {annotations_count} annotation(s) from {len(updates)} existing task(s) in {self}.')

    def _create_tasks_from_table(self, t: Table, col_mapping: dict[str, str], existing_tasks: list[dict]) -> None:
        row_ids_in_ls = {tuple(task['meta']['rowid']) for task in existing_tasks}
        t_col_types = t.column_types()
        t_push_cols = [
            t_col_name for t_col_name, r_col_name in col_mapping.items()
            if r_col_name in self.get_push_columns()
        ]
        r_push_cols = [col_mapping[col_name] for col_name in t_push_cols]
        for col_name in t_push_cols:
            if t_col_types[col_name].is_media_type() and not t[col_name].col.is_stored:
                raise excs.Error(
                    f'Media column linked to a `LabelStudioProject` is not a stored column: `{col_name}`'
                )
        if len(t_push_cols) == 1 and t_col_types[t_push_cols[0]].is_media_type():
            # With a single media column, we can push local files to Label Studio using
            # the file transfer API.
            col_name = t_push_cols[0]
            # Select `t[col_name]` as well as `t[col_name].localpath` to ensure that
            # the image file is properly cached and `localpath` is defined
            rows = t.select(t[col_name], t[col_name].localpath)
            tasks_created = 0
            for row in rows._exec():
                if row.rowid not in row_ids_in_ls:
                    file = Path(row.vals[-1])
                    # Upload the media file to Label Studio
                    task_id: int = self.project.import_tasks(file)[0]
                    # Assemble the remaining columns into `data`
                    self.project.update_task(task_id, meta={'rowid': row.rowid})
                    tasks_created += 1
            print(f'Created {tasks_created} new task(s) in {self}.')
        else:
            # Either a single non-media column or multiple columns. Either way, we can't
            # use the file upload API and need to rely on externally accessible URLs for
            # media columns.
            selection = [
                t[col_name].fileurl if t_col_types[col_name].is_media_type() else t[col_name]
                for col_name in t_push_cols
            ]
            rows = t.select(*selection)
            new_rows = filter(lambda row: row.rowid not in row_ids_in_ls, rows._exec())
            for page in more_itertools.batched(new_rows, n=_PAGE_SIZE):
                tasks = []
                # Validate media columns
                for row in page:
                    for i in range(len(row.vals)):
                        if t[t_push_cols[i]].col_type.is_media_type() and row.vals[i].startswith("file://"):
                            raise excs.Error(
                                'Cannot use locally stored media files in a `LabelStudioProject` with more than one '
                                'field. (This is a limitation of Label Studio; see warning here: '
                                'https://labelstud.io/guide/tasks.html)'
                            )
                    tasks.append({
                        'data': zip(r_push_cols, row.vals),
                        'meta': {'rowid': row.rowid}
                    })
                self.project.import_tasks(tasks)

    def to_dict(self) -> dict[str, Any]:
        return {'project_id': self.project_id}

    @classmethod
    def from_dict(cls, md: dict[str, Any]) -> LabelStudioProject:
        return LabelStudioProject(md['project_id'])

    def __repr__(self) -> str:
        name = self.project.get_params()['title']
        return f'LabelStudioProject `{name}`'

    @classmethod
    def _parse_project_config(cls, config: str) -> dict[str, ts.ColumnType]:
        """
        Parses a Label Studio XML config, extracting the names and Pixeltable types of
        all input variables.
        """
        root: ElementTree.Element = ElementTree.fromstring(config)
        if root.tag.lower() != 'view':
            raise excs.Error('Root of Label Studio config must be a `View`')
        assert root.tag == 'View'
        return dict(cls._extract_vars_from_project_config(root))

    @classmethod
    def _extract_vars_from_project_config(cls, root: ElementTree.Element) -> Iterator[(str, ts.ColumnType)]:
        for element in root:
            if 'value' in element.attrib and element.attrib['value'][0] == '$':
                element_type = _LS_TAG_MAP.get(element.tag.lower())
                if element_type is None:
                    raise excs.Error(f'Unsupported Label Studio data type: `{element.tag}`')
                yield element.attrib['value'][1:], element_type


_PAGE_SIZE = 100  # This is the default used in the LS SDK
_LS_TAG_MAP = {
    'text': ts.StringType(),
    'image': ts.ImageType(),
    'video': ts.VideoType(),
    'audio': ts.AudioType()
}