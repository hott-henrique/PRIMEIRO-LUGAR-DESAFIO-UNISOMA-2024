import logging

import threading

import time

import zipfile

import typing as t

import tkinter as tk

import tkinter.ttk
import tkinter.filedialog
import tkinter.messagebox

import pulp

from app.loader.Loader import Loader
from app.model.Model import Model
from app.export.excel import save_errors, save_output


class InfiniteThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        output = super().run()

        super().__init__(*self.args, **self.kwargs)

        return output

class TkLoggerHandler(logging.Handler):

    def __init__(self, text: tk.Text, level = 0):
        self.text = text
        super().__init__(level)

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)

        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, msg + '\n')
        self.text.config(state=tk.DISABLED)
        self.text.yview(tk.END)
        self.text.update()

def create_logger(text: tk.Text, fmt: str = '%(asctime)s: %(message)s'):
    handler = TkLoggerHandler(text=text)

    formatter = logging.Formatter(fmt=fmt, datefmt='%Y-%m-%d %H:%M:%S')

    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger

def create_file_selector(master: tk.Misc, on_file_selected: t.Callable):
    selector_frame = tk.Frame(master)

    label = tk.Label(master=selector_frame, text="Arquivo: ")

    file_path_input: tk.Text

    def set_file_path():
        file = tkinter.filedialog.askopenfilename(filetypes=[ ("Excel files", ".xlsx .xls") ])

        if file:
            file = file.strip()
            file_path_input.delete(1.0, tk.END)
            file_path_input.insert(tk.END, file)

        on_file_selected(file)

    file_selector_btn = tk.Button(master=selector_frame, text="Escolher", command=set_file_path)

    file_path_input: tk.Text = tk.Text(master=selector_frame, height=file_selector_btn.winfo_height())

    label.grid(row=0, column=0)
    file_path_input.grid(row=0, column=1)
    file_selector_btn.grid(row=0, column=2)

    return selector_frame

def main():
    window = tk.Tk()

    window.wm_title("Agendador de Pacientes")
    window.wm_minsize(300, 400)

    message_title = tk.Label(master=window, text="Processamento")
    message = tk.Text(master=window, state='disabled')

    logger = create_logger(text=message)

    loader = Loader(logger=logger)

    def set_file_path(path):
        loader.file_path = path

    selector_frame = create_file_selector(master=window, on_file_selected=set_file_path)

    progress_bar = tkinter.ttk.Progressbar(window, maximum=4)

    proccess_btn: tk.Button

    def process():
        if not loader.file_path:
            tkinter.messagebox.showerror("Erro ao realizar agendamento.", "Por favor, selecione um arquivo.")
            return

        proccess_btn["state"] = "disabled"
        progress_bar["value"] = 1
        window.update()

        logger.info(f"Carregando arquivo: {loader.file_path}")

        try:
            data = loader.load()

            progress_bar["value"] = 2
            window.update()

            logger.info(f"Realizando agendamento, este processo pode levar algum tempo, por favor, aguarde.")

            model = Model(logger=logger)

            solution, status, time_elapsed = model.optimze(data)

            map_status_to_message = {
                "Not Solved": "Não Resolvido",
                "Optimal": "Ótimo",
                "Infeasible": "Inviável",
                "Unbounded": "Ilimitado",
                "Undefined": "Indefinido"
            }

            logger.info(f"Resultado do processamento: {map_status_to_message[status]}.")
            logger.info(f"Tempo gasto: {time_elapsed:.2f} segundos.")

            logger.debug(solution)

            if status == "Optimal":
                logger.info(f"Salvando resultados.")

                save_output(loader.file_path, data, solution, logger=logger)

                progress_bar["value"] = 3
                window.update()

            progress_bar["value"] = 4
        except zipfile.BadZipFile as e:
            logger.info(f"O carregamento falhou, por favor verifique se o arquivo excel está corrompido.")
            progress_bar["value"] = 0
        except Exception as e:
            import traceback
            logger.debug(traceback.format_exc())
            logger.info(f"O processamento falhou, por favor verifique os erros.")
            progress_bar["value"] = 0

        try:
            logger.info(f"Salvando os erros.")
            save_errors(loader.file_path, loader.errors, logger=logger)
        except zipfile.BadZipFile as e:
            logger.info(f"O programa falhou ao salvar os errors, por favor verifique se o arquivo excel está corrompido.")

        proccess_btn["state"] = "normal"
        window.update()

    proccess_btn = tk.Button(
        text="Agendar",
        width=window.winfo_width(),
        command=InfiniteThread(target=process).start
    )

    selector_frame.grid(row=0)
    message_title.grid(row=1, sticky="news", padx=0)
    message.grid(row=2, sticky="news", padx=0)
    progress_bar.grid(row=3, sticky="nesw", padx=0)
    proccess_btn.grid(row=4, sticky="nesw", padx=0)

    window.mainloop()

if __name__ == "__main__":
    main()
