import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from avito_parser.scraper import run_scraping, ScrapingCancelled


class AvitoParserApp:
    """Главное окно приложения Avito Parser."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Avito Parser")
        self.root.geometry("720x560")
        self.root.minsize(640, 480)

        self.cookies_path: str | None = None
        self.output_path: str | None = None
        self.worker_thread: threading.Thread | None = None
        self.cancel_requested = False

        self._build_ui()


    def _build_ui(self):
        """Построение графического интерфейса."""
        pad = {"padx": 10, "pady": 6}

        # Ссылка
        frm_url = ttk.LabelFrame(self.root, text="Ссылка на страницу Avito")
        frm_url.pack(fill="x", **pad)
        self.url_entry = ttk.Entry(frm_url, font=("Segoe UI", 10))
        self.url_entry.pack(fill="x", padx=8, pady=8)
        self.url_entry.insert(0, "https://www.avito.ru/...")

        # Параметры: страницы + cookies
        frm_params = ttk.LabelFrame(self.root, text="Параметры")
        frm_params.pack(fill="x", **pad)

        row1 = ttk.Frame(frm_params)
        row1.pack(fill="x", padx=8, pady=4)
        ttk.Label(row1, text="Количество страниц:").pack(side="left")
        self.pages_var = tk.IntVar(value=5)
        self.pages_spin = ttk.Spinbox(row1, from_=1, to=100, width=6, textvariable=self.pages_var)
        self.pages_spin.pack(side="left", padx=8)

        row2 = ttk.Frame(frm_params)
        row2.pack(fill="x", padx=8, pady=4)
        ttk.Label(row2, text="Файл cookies.txt:").pack(side="left")
        self.cookies_label = ttk.Label(row2, text="(не выбран — парсинг без авторизации)", foreground="#888")
        self.cookies_label.pack(side="left", padx=8)
        ttk.Button(row2, text="Выбрать файл...", command=self._choose_cookies).pack(side="right")

        row3 = ttk.Frame(frm_params)
        row3.pack(fill="x", padx=8, pady=4)
        ttk.Label(row3, text="Куда сохранить результат:").pack(side="left")
        self.output_label = ttk.Label(row3, text="avito_results.xlsx (в папке программы)", foreground="#888")
        self.output_label.pack(side="left", padx=8)
        ttk.Button(row3, text="Выбрать...", command=self._choose_output).pack(side="right")

        # Кнопки управления
        frm_actions = ttk.Frame(self.root)
        frm_actions.pack(fill="x", **pad)
        self.start_btn = ttk.Button(frm_actions, text="▶ Начать парсинг", command=self._on_start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(frm_actions, text="■ Остановить", command=self._on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        self.open_file_btn = ttk.Button(frm_actions, text="Открыть результат", command=self._open_result, state="disabled")
        self.open_file_btn.pack(side="right")

        # Прогресс
        frm_progress = ttk.Frame(self.root)
        frm_progress.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(frm_progress, mode="determinate")
        self.progress.pack(fill="x")
        self.status_label = ttk.Label(frm_progress, text="Готов к запуску.")
        self.status_label.pack(anchor="w", pady=(4, 0))

        # Лог
        frm_log = ttk.LabelFrame(self.root, text="Журнал")
        frm_log.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(frm_log, height=12, state="disabled", wrap="word", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)


    def _choose_cookies(self):
        """Диалог выбора файла cookies"""
        path = filedialog.askopenfilename(
            title="Выбери файл cookies.txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
        )
        if path:
            self.cookies_path = path
            self.cookies_label.config(text=os.path.basename(path), foreground="#000")

    def _choose_output(self):
        """Диалог выбора файла для сохранения результата"""
        path = filedialog.asksaveasfilename(
            title="Куда сохранить результат",
            defaultextension=".xlsx",
            initialfile="avito_results.xlsx",
            filetypes=[("Excel файл", "*.xlsx")],
        )
        if path:
            self.output_path = path
            self.output_label.config(text=os.path.basename(path), foreground="#000")

    def _open_result(self):
        """Открыть результирующий файл в ОС"""
        if self.output_path and os.path.exists(self.output_path):
            if sys.platform.startswith("win"):
                os.startfile(self.output_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.output_path])
            else:
                subprocess.run(["xdg-open", self.output_path])

    def _on_start(self):
        """Начать парсинг"""
        url = self.url_entry.get().strip()
        if not (url.startswith("https://www.avito.ru/") or url.startswith("https://avito.ru/")):
            messagebox.showerror("Ошибка", "Вставь корректную ссылку на avito.ru")
            return

        max_pages = self.pages_var.get()
        output_file = self.output_path or "avito_results.xlsx"
        self.output_path = output_file

        self.cancel_requested = False
        self._set_running_state(True)
        self._clear_log()
        self.progress.config(maximum=max_pages, value=0)

        self.worker_thread = threading.Thread(
            target=self._run_worker,
            args=(url, max_pages, output_file, self.cookies_path),
            daemon=True,
        )
        self.worker_thread.start()

    def _on_stop(self):
        self.cancel_requested = True
        self._append_log("Останавливаю после текущей страницы...")


    def _run_worker(self, url, max_pages, output_file, cookies_file):
        """Рабочий поток для парсинга"""
        try:
            count, path = run_scraping(
                start_url=url,
                max_pages=max_pages,
                output_file=output_file,
                cookies_file=cookies_file,
                log_callback=lambda msg: self.root.after(0, self._append_log, msg),
                progress_callback=lambda cur, total: self.root.after(0, self._update_progress, cur, total),
                should_cancel=lambda: self.cancel_requested,
            )
            self.root.after(0, self._on_finished, count, path)
        except ScrapingCancelled:
            self.root.after(0, self._on_cancelled)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))
            

    def _append_log(self, msg: str):
        """Добавить строку в логе"""
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.status_label.config(text=msg)

    def _clear_log(self):
        """Очистить лог"""
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _update_progress(self, current: int, total: int):
        """Обновить полоску прогресса"""
        self.progress.config(maximum=total, value=current)

    def _set_running_state(self, running: bool):
        """Обновить состояние кнопок при запуске/остановке"""
        self.start_btn.config(state="disabled" if running else "normal")
        self.stop_btn.config(state="normal" if running else "disabled")
        self.open_file_btn.config(state="disabled")

    def _on_finished(self, count: int, path: str):
        """Обработка завершения парсинга"""
        self._set_running_state(False)
        self.open_file_btn.config(state="normal" if count else "disabled")
        self.status_label.config(text=f"Готово! Собрано объявлений: {count}")
        if count:
            messagebox.showinfo("Готово", f"Собрано {count} объявлений.\nФайл: {path}")
        else:
            messagebox.showwarning("Нет данных", "Не удалось собрать ни одного объявления. Смотри журнал.")

    def _on_cancelled(self):
        """Обработка отмены парсинга"""
        self._set_running_state(False)
        self.status_label.config(text="Остановлено пользователем.")

    def _on_error(self, error_msg: str):
        """Обработка ошибок"""
        self._set_running_state(False)
        self.status_label.config(text="Произошла ошибка.")
        messagebox.showerror("Ошибка", f"Что-то пошло не так:\n{error_msg}")


def main():
    """Главная функция запуска приложения"""
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    app = AvitoParserApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
