from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Tags(_message.Message):
    __slots__ = ("code_md5", "files", "tags")
    CODE_MD5_FIELD_NUMBER: _ClassVar[int]
    FILES_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    code_md5: str
    files: _containers.RepeatedCompositeFieldContainer[File]
    tags: _containers.RepeatedCompositeFieldContainer[Tag]
    def __init__(self, code_md5: _Optional[str] = ..., files: _Optional[_Iterable[_Union[File, _Mapping]]] = ..., tags: _Optional[_Iterable[_Union[Tag, _Mapping]]] = ...) -> None: ...

class File(_message.Message):
    __slots__ = ("path", "language", "md5", "lines")
    PATH_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    MD5_FIELD_NUMBER: _ClassVar[int]
    LINES_FIELD_NUMBER: _ClassVar[int]
    path: str
    language: str
    md5: str
    lines: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, path: _Optional[str] = ..., language: _Optional[str] = ..., md5: _Optional[str] = ..., lines: _Optional[_Iterable[int]] = ...) -> None: ...

class Tag(_message.Message):
    __slots__ = ("file", "start", "length", "skip")
    FILE_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    SKIP_FIELD_NUMBER: _ClassVar[int]
    file: int
    start: int
    length: int
    skip: int
    def __init__(self, file: _Optional[int] = ..., start: _Optional[int] = ..., length: _Optional[int] = ..., skip: _Optional[int] = ...) -> None: ...
