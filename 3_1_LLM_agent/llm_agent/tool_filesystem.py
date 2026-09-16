import json
from pathlib import Path
from typing import Any, Dict, Union


class FileSystemTool:
    """
    Инструмент для безопасной работы с файлами внутри sandbox.

    Поддерживаемые операции:
    - read
    - write
    - list
    - delete
    """

    name = "filesystem"

    description = (
        "Безопасная работа с файлами внутри sandbox: "
        "чтение, запись, просмотр списка файлов и удаление."
    )

    def __init__(self, sandbox_dir: Union[str, Path, None] = None):
        """
        Инициализация инструмента.

        Если sandbox_dir не передан, используется директория
        3_1_LLM_agent/sandbox.
        """

        if sandbox_dir is None:
            sandbox_dir = (
                Path(__file__).resolve().parent.parent
                / "sandbox"
            )

        self.sandbox_dir = Path(sandbox_dir).resolve()

        # Если директории ещё нет — создаём её.
        self.sandbox_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def _get_safe_path(self, user_path: str) -> Path:
        """
        Преобразует путь пользователя в путь внутри sandbox
        и запрещает выход за его пределы.
        """

        if not isinstance(user_path, str):
            raise TypeError(
                "Путь должен быть строкой."
            )

        if not user_path.strip():
            raise ValueError(
                "Путь не может быть пустым."
            )

        path = Path(user_path)

        # Запрещаем абсолютные пути:
        # /etc/passwd
        # /Users/name/file.txt
        if path.is_absolute():
            raise ValueError(
                "Абсолютные пути запрещены."
            )

        # Соединяем sandbox + пользовательский путь.
        #
        # Например:
        # sandbox + notes/test.txt
        #
        # После resolve():
        # /.../sandbox/notes/test.txt
        target_path = (
            self.sandbox_dir / path
        ).resolve()

        # Проверка безопасности.
        #
        # Если пользователь передал:
        # ../../etc/passwd
        #
        # resolve() превратит это в путь,
        # который уже НЕ находится внутри sandbox.
        try:
            target_path.relative_to(
                self.sandbox_dir
            )
        except ValueError:
            raise ValueError(
                "Выход за пределы sandbox запрещён."
            )

        return target_path

    def read(self, path: str) -> str:
        """
        Читает текстовый файл из sandbox.
        """

        file_path = self._get_safe_path(path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Файл '{path}' не найден."
            )

        if not file_path.is_file():
            raise IsADirectoryError(
                f"'{path}' не является файлом."
            )

        return file_path.read_text(
            encoding="utf-8"
        )

    def write(
        self,
        path: str,
        content: str
    ) -> str:
        """
        Записывает текст в файл внутри sandbox.

        Если вложенных директорий нет,
        они будут автоматически созданы.
        """

        if not isinstance(content, str):
            raise TypeError(
                "Содержимое файла должно быть строкой."
            )

        file_path = self._get_safe_path(path)

        # Например:
        # notes/test.txt
        #
        # если notes ещё не существует —
        # создаём её.
        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        relative_path = file_path.relative_to(
            self.sandbox_dir
        )

        return (
            f"Файл '{relative_path}' успешно записан."
        )

    def list(self, path: str = ".") -> str:
        """
        Показывает содержимое директории внутри sandbox.
        """

        directory_path = self._get_safe_path(
            path
        )

        if not directory_path.exists():
            raise FileNotFoundError(
                f"Директория '{path}' не найдена."
            )

        if not directory_path.is_dir():
            raise NotADirectoryError(
                f"'{path}' не является директорией."
            )

        items = sorted(
            directory_path.iterdir(),
            key=lambda item: item.name.lower()
        )

        if not items:
            return "Директория пуста."

        result = []

        for item in items:
            relative_path = item.relative_to(
                self.sandbox_dir
            )

            if item.is_dir():
                result.append(
                    f"[DIR] {relative_path}"
                )
            else:
                result.append(
                    f"[FILE] {relative_path}"
                )

        return "\n".join(result)

    def delete(self, path: str) -> str:
        """
        Удаляет файл внутри sandbox.

        Директории удалять нельзя.
        """

        file_path = self._get_safe_path(path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Файл '{path}' не найден."
            )

        if not file_path.is_file():
            raise IsADirectoryError(
                "Удаление директорий "
                "не поддерживается."
            )

        relative_path = file_path.relative_to(
            self.sandbox_dir
        )

        file_path.unlink()

        return (
            f"Файл '{relative_path}' успешно удалён."
        )

    def use(
        self,
        tool_input: Union[
            str,
            Dict[str, Any]
        ]
    ) -> str:
        """
        Главный метод инструмента.

        Именно его вызывает LLMAgent:

            self.tools[tool_name].use(tool_input)

        Поддерживает два варианта входных данных:

        1. Python-словарь:

        {
            "operation": "write",
            "path": "hello.txt",
            "content": "Hello"
        }

        2. JSON-строку:

        '{"operation": "read", "path": "hello.txt"}'
        """

        try:
            # Если модель передала JSON как строку,
            # преобразуем её в словарь.
            if isinstance(tool_input, str):
                data = json.loads(tool_input)

            # Если модель сразу передала JSON-объект,
            # json.loads уже не нужен.
            elif isinstance(tool_input, dict):
                data = tool_input

            else:
                raise TypeError(
                    "Вход инструмента должен быть "
                    "JSON-объектом или JSON-строкой."
                )

            operation = data.get("operation")

            if not isinstance(
                operation,
                str
            ):
                raise ValueError(
                    "Необходимо указать "
                    "строковое поле 'operation'."
                )

            operation = (
                operation
                .strip()
                .lower()
            )

            if operation == "read":
                path = data.get("path")

                if not isinstance(path, str):
                    raise ValueError(
                        "Для read необходимо "
                        "указать поле 'path'."
                    )

                return self.read(path)

            elif operation == "write":
                path = data.get("path")
                content = data.get("content")

                if not isinstance(path, str):
                    raise ValueError(
                        "Для write необходимо "
                        "указать поле 'path'."
                    )

                if not isinstance(content, str):
                    raise ValueError(
                        "Для write необходимо "
                        "указать строковое "
                        "поле 'content'."
                    )

                return self.write(
                    path,
                    content
                )

            elif operation == "list":
                path = data.get(
                    "path",
                    "."
                )

                if not isinstance(path, str):
                    raise ValueError(
                        "Поле 'path' должно "
                        "быть строкой."
                    )

                return self.list(path)

            elif operation == "delete":
                path = data.get("path")

                if not isinstance(path, str):
                    raise ValueError(
                        "Для delete необходимо "
                        "указать поле 'path'."
                    )

                return self.delete(path)

            else:
                raise ValueError(
                    "Неизвестная операция. "
                    "Допустимые операции: "
                    "read, write, list, delete."
                )

        except (
            json.JSONDecodeError,
            OSError,
            TypeError,
            ValueError
        ) as error:

            return (
                "Ошибка FileSystemTool: "
                f"{error}"
            )