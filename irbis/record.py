# coding: utf-8

"""
Работа с записями, полями, подполями.
"""

from typing import Iterable, List, Optional, Set, Union
from irbis._common import LOGICALLY_DELETED, PHYSICALLY_DELETED
from irbis.field import Field
from irbis.subfield import SubField


class Record:
    """
    MARC record with MFN, status, version and fields.
    """

    __slots__ = 'database', 'mfn', 'version', 'status', 'fields'

    def __init__(self, *fields: Field) -> None:
        self.database: Optional[str] = None
        self.mfn: int = 0
        self.version: int = 0
        self.status: int = 0
        self.fields: List[Field] = []
        self.fields.extend(fields)

    def add(self, tag: int, value: Union[str, SubField] = None) \
            -> 'Field':
        """
        Добавление поля (возможно, с значением и подполями) к записи.

        :param tag: Метка поля.
        :param value: Значение поля (опционально)
        :return: Свежедобавленное поле
        """
        assert tag > 0

        if isinstance(value, str):
            result = Field(tag, value)
        else:
            result = Field(tag)
            if isinstance(value, SubField):
                result.subfields.append(value)

        self.fields.append(result)
        return result

    def add_non_empty(self, tag: int,
                      value: Union[str, SubField]) -> 'Record':
        """
        Добавление поля, если его значение не пустое.

        :param tag: Метка поля.
        :param value: Значение поля (опционально).
        :return: Self
        """
        assert tag > 0

        if value:
            if isinstance(value, str):
                field = Field(tag, value)
            else:
                field = Field(tag)
                if isinstance(value, SubField):
                    field.subfields.append(value)

            self.fields.append(field)

        return self

    def all(self, tag: int) -> List[Field]:
        """
        Список полей с указанной меткой.

        :param tag: Тег
        :return: Список полей (возможно, пустой)
        """
        assert tag > 0

        return [f for f in self.fields if f.tag == tag]

    def all_as_dict(self, tag: int) -> List[dict]:
        """
        Список полей с указанной меткой, каждое поле в виде словаря
        "код - значение".
        :param tag:
        :return:
        """
        assert tag > 0

        return [f.to_dict() for f in self.fields if f.tag == tag]

    def clear(self) -> 'Record':
        """
        Очистка записи (удаление всех полей).

        :return: Self
        """
        self.fields.clear()
        return self

    def clone(self) -> 'Record':
        """
        Клонирование записи.

        :return: Полный клон записи
        """
        result = Record()
        result.database = self.database
        result.mfn = self.mfn
        result.status = self.status
        result.version = self.version
        result.fields = [field.clone() for field in self.fields]
        return result

    def encode(self) -> List[str]:
        """
        Кодирование записи в серверное представление.

        :return: Список строк
        """
        result = [str(self.mfn) + '#' + str(self.status),
                  '0#' + str(self.version)]
        for field in self.fields:
            result.append(str(field))
        return result

    def fm(self, tag: int, code: str = '') -> Optional[str]:
        """
        Текст первого поля с указанной меткой.
        :param tag: Искомая метка поля
        :param code: Код (опционально)
        :return: Текст или None
        """
        assert tag > 0

        for field in self.fields:
            if field.tag == tag:
                if code:
                    return field.first_value(code)
                return field.value
        return None

    def fma(self, tag: int, code: str = '') -> List[str]:
        """
        Спосок значений полей с указанной меткой.
        Пустые значения в список не включаются.

        :param tag: Искомая метка поля
        :param code: Код (опционально)
        :return: Список с текстами (м. б. пустой)
        """
        assert tag > 0

        result = []
        for field in self.fields:
            if field.tag == tag:
                if code:
                    one = field.first_value(code)
                    if one:
                        result.append(one)
                else:
                    one = field.value
                    if one:
                        result.append(one)
        return result

    def first(self, tag: int) -> Optional[Field]:
        """
        Первое из полей с указанной меткой.

        :param tag: Искомая метка поля
        :return: Поле либо None
        """
        assert tag > 0

        for field in self.fields:
            if field.tag == tag:
                return field
        return None

    def first_as_dict(self, tag: int) -> dict:
        """
        Первое из полей с указанной меткой в виде словаря
        "код - значение".
        """
        assert tag > 0

        for field in self.fields:
            if field.tag == tag:
                return field.to_dict()
        return {}

    def have_field(self, tag: int) -> bool:
        """
        Есть ли в записи поле с указанной меткой?

        :param tag: Искомая метка поля.
        :return: True или False.
        """
        assert tag > 0

        for field in self.fields:
            if field.tag == tag:
                return True

        return False

    def insert_at(self, index: int, tag: int, value: Optional[str] = None) \
            -> Field:
        """
        Вставка поля в указанной позиции.

        :param index: Позиция для вставки.
        :param tag: Метка поля.
        :param value: Значение поля до первого разделитея (опционально).
        :return: Self
        """
        assert 0 <= index < len(self.fields)
        assert tag > 0

        result = Field(tag, value)
        self.fields.insert(index, result)
        return result

    def is_deleted(self) -> bool:
        """
        Удалена ли запись?
        :return: True для удаленной записи
        """
        return (self.status & (LOGICALLY_DELETED | PHYSICALLY_DELETED)) != 0

    def keys(self) -> Set[int]:
        """
        Получение множества меток полей

        :return: множество меток
        """
        return set(field.tag for field in self.fields)

    # noinspection DuplicatedCode
    def parse(self, text: List[str]) -> None:
        """
        Разбор текстового представления записи (в серверном формате).

        :param text: Список строк
        :return: None
        """
        if not text:
            return

        line = text[0]
        parts = line.split('#')
        self.mfn = int(parts[0])
        if len(parts) != 1 and parts[1]:
            self.status = int(parts[1])
        line = text[1]
        parts = line.split('#')
        self.version = int(parts[1])
        self.fields.clear()
        for line in text[2:]:
            field = Field()
            field.parse(line)
            self.fields.append(field)

    def remove_at(self, index: int) -> 'Record':
        """
        Удаление поля в указанной позиции.

        :param index: Позиция для удаления.
        :return: Self
        """
        assert 0 <= index < len(self.fields)

        self.fields.remove(self.fields[index])
        return self

    def remove_field(self, tag: int) -> 'Record':
        """
        Удаление полей с указанной меткой.

        :param tag: Метка поля.
        :return: Self.
        """
        assert tag > 0

        index = 0
        while index < len(self.fields):
            field = self.fields[index]
            if field.tag == tag:
                self.fields.remove(field)
            else:
                index += 1

        return self

    def reset(self) -> 'Record':
        """
        Сбрасывает состояние записи, отвязывая её от базы данных.
        Поля при этом остаются нетронутыми.
        :return: Self.
        """
        self.mfn = 0
        self.status = 0
        self.version = 0
        self.database = None
        return self

    def set_field(self, tag: int, value: Optional[str]) -> 'Record':
        """
        Устанавливает значение первого повторения указанного поля.
        Если указанное значение пустое, поле удаляется из записи.

        :param tag: Метка поля.
        :param value: Значение поля до первого разделителя (может быть None).
        :return: Self.
        """
        assert tag > 0

        found = self.first(tag)
        if value:
            if not found:
                found = Field(tag)
                self.fields.append(found)
            found.value = value
        else:
            if found:
                self.fields.remove(found)

        return self

    def set_subfield(self, tag: int, code: str,
                     value: Optional[str]) -> 'Record':
        """
        Устанавливает значение подполя в первом повторении указанного поля.
        Если указанное значение пустое, подполе удаляется из поля.

        :param tag: Метка поля.
        :param code: Код подполя.
        :param value: Значение подполя (может быть None).
        :return: Self.
        """
        assert tag > 0
        assert len(code) == 1

        found = self.first(tag)
        if value:
            if not found:
                found = Field(tag)
                self.fields.append(found)
        if found:
            found.set_subfield(code, value)

        return self

    def __str__(self):
        result = [str(field) for field in self.fields]
        return '\n'.join(result)

    def __iter__(self):
        """
        Перебор полей записи для формирования словаря "код - поля".
        """
        accumulator = {}
        for field in self.fields:
            key = field.tag

            if field.subfields:
                value = dict(field)
            else:
                value = field.value

            value_count = len(self.all(key))
            if value_count == 1:
                accumulator[key] = value
            elif value_count > 1:
                if key not in accumulator:
                    accumulator[key] = [value]
                else:
                    accumulator[key].append(value)

        for key, value in accumulator.items():
            yield key, value

    def __iadd__(self, other: Union[Field, Iterable[Field]]):
        if isinstance(other, Field):
            self.fields.append(other)
        else:
            self.fields.extend(other)
        return self

    def __isub__(self, other: Union[Field, Iterable[Field]]):
        if isinstance(other, Field):
            if other in self.fields:
                self.fields.remove(other)
        else:
            for one in other:
                if one in self.fields:
                    self.fields.remove(one)
        return self

    def __getitem__(self, tag: int) -> Union[dict, List[dict], str]:
        """
        Получение значения поля по индексу

        :param tag: числовая метка поля
        :return: словарь, список словарей или строку со значением поля
        """
        def get_str_or_dict(field):
            if field.subfields:
                return dict(field)
            return field.value

        fields = self.all(tag)
        count = len(fields)

        if count == 1:
            return get_str_or_dict(fields[0])

        if count > 1:
            return [get_str_or_dict(field) for field in fields]

        return ''

    def __setitem__(self, key: int,
                    value: Union[Field, SubField, str, None]):
        if value is None:
            found: List[Field] = self.all(key)
            for fld in found:
                self.fields.remove(fld)
            return

        field: Optional[Field] = self.first(key)
        if isinstance(value, str):
            if field is None:
                field = Field(key, value)
                self.fields.append(field)
            else:
                field.clear()
                field.headless_parse(value)

        if isinstance(value, Field):
            if field is None:
                field = Field(key)
                self.fields.append(field)
            value.tag = key
            field.assign_from(value)

        if isinstance(value, SubField):
            if field is None:
                field = Field(key)
                self.fields.append(field)
            field.clear()
            field.subfields.append(value)

    def __len__(self):
        return len(self.fields)

    def __bool__(self):
        return bool(self.fields)


class RawRecord:
    """
    Запись с нераскодированными полями/подполями.
    """

    __slots__ = 'database', 'mfn', 'status', 'version', 'fields'

    def __init__(self, *fields: str) -> None:
        self.database: Optional[str] = None
        self.mfn: int = 0
        self.version: int = 0
        self.status: int = 0
        self.fields: List[str] = []
        self.fields.extend(fields)

    def clear(self) -> 'RawRecord':
        """
        Очистка записи (удаление всех полей).

        :return: Self
        """
        self.fields.clear()
        return self

    def clone(self) -> 'RawRecord':
        """
        Клонирование записи.

        :return: Полный клон записи
        """
        result = RawRecord()
        result.database = self.database
        result.mfn = self.mfn
        result.status = self.status
        result.version = self.version
        result.fields = list(field for field in self.fields)
        return result

    def encode(self) -> List[str]:
        """
        Кодирование записи в серверное представление.

        :return: Список строк
        """
        result = [str(self.mfn) + '#' + str(self.status),
                  '0#' + str(self.version)]
        for field in self.fields:
            result.append(field)
        return result

    def is_deleted(self) -> bool:
        """
        Удалена ли запись?
        :return: True для удаленной записи
        """
        return (self.status & (LOGICALLY_DELETED | PHYSICALLY_DELETED)) != 0

    # noinspection DuplicatedCode
    def parse(self, text: List[str]) -> None:
        """
        Разбор текстового представления записи (в серверном формате).

        :param text: Список строк
        :return: None
        """

        if not text:
            return

        line = text[0]
        parts = line.split('#')
        self.mfn = int(parts[0])
        if len(parts) != 1 and parts[1]:
            self.status = int(parts[1])
        line = text[1]
        parts = line.split('#')
        self.version = int(parts[1])
        self.fields.clear()
        for line in text[2:]:
            self.fields.append(line)

    def remove_at(self, index: int) -> 'RawRecord':
        """
        Удаление поля в указанной позиции.

        :param index: Позиция для удаления.
        :return: Self
        """
        assert 0 <= index < len(self.fields)

        self.fields.remove(self.fields[index])
        return self

    def reset(self) -> 'RawRecord':
        """
        Сбрасывает состояние записи, отвязывая её от базы данных.
        Поля при этом остаются нетронутыми.
        :return: Self.
        """
        self.mfn = 0
        self.status = 0
        self.version = 0
        self.database = None
        return self

    def __str__(self):
        result = [str(field) for field in self.fields]
        return '\n'.join(result)

    def __iter__(self):
        yield from self.fields

    def __len__(self):
        return len(self.fields)

    def __bool__(self):
        return bool(len(self.fields))


__all__ = ['Field', 'RawRecord', 'Record', 'SubField']
