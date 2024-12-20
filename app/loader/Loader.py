import pandas as pd
import numpy as np
from collections import defaultdict


import logging


WEEK_SIZE = 6
HOUR_PER_DAY = 13

class Loader(object):

    def __init__(self, logger: logging.Logger = logging.getLogger(__module__)):
        self.logger = logger
        self.file_path = str()
        self.errors = list()

    def load(self):
        self.errors.clear()

        data = self.load_data()

        response = dict()

        response['days'] = np.arange(WEEK_SIZE)
        response['hours'] = np.arange(HOUR_PER_DAY)

        disp_m_response = self.create_disp_m(data['RegraProfissional'])
        competence_m_p_response = self.create_competence_m_p(data['RegraProfissional'], data['IdadePaciente'])
        local_m_l_response = self.create_local_m_l(data['LocalProfissional'])

        response['doctors'] = disp_m_response[0]
        response['doctor_names'] = disp_m_response[1]
        response['patientes'] = competence_m_p_response[0]
        response['patient_names'] = competence_m_p_response[1]
        response['locals'] = local_m_l_response[0]
        response['local_names'] = local_m_l_response[1]
        response['disp_m'] = disp_m_response[2]
        response['competence_m_p'] = competence_m_p_response[2]
        response['local_m_l'] = local_m_l_response[2]
        response['local_p_l_d'] = self.create_local_p_l_d(data['LocalPaciente'], data['IdadePaciente'])
        response['dispon_p_d_h'] = self.create_dispon_p_d_h(data['DisponPaciente'])
        response['dispon_m_d_h'] = self.create_dispon_m_d_h(data['DisponProfissional'])

        return response

    def load_data(self) -> dict:
        default_sheets = [
            'IdadePaciente',
            'DisponPaciente',
            'LocalPaciente',
            'RegraProfissional',
            'DisponProfissional',
            'LocalProfissional'
        ]

        loaded_sheet = pd.ExcelFile(self.file_path)

        has_all_sheets = all(e in loaded_sheet.sheet_names for e in default_sheets)

        if not has_all_sheets:
            raise Exception("Improper file")

        # TODO: Check for errors in tables.

        data = {
            sheet_name: pd.read_excel(self.file_path, sheet_name=sheet_name).fillna(0) for sheet_name in default_sheets
        }
        
        for sheet_name, sheet_data in data.items():
            column_name = 'paciente' if 'Paciente' in sheet_name else 'profissional'
            data[sheet_name] = self.before_verify_duplicate(sheet_data, column_name)
            data[sheet_name] = self.verify_duplicate(data[sheet_name], sheet_name, column_name)
            data[sheet_name] = self.after_verify_duplicate(sheet_data, column_name)
            print(data[sheet_name].head(8))


        return data


    def before_verify_duplicate(self, data: pd.DataFrame, column_name: str):

        current_name = None
        idx = 0
        new_column = []
        for _, row in data.iterrows():
            if row[column_name] != 0:
                current_name = row[column_name]
                idx = 0
                new_column.append(current_name)
            else:
                new_column.append(current_name + "#" + str(idx))
                idx += 1

        data[column_name] = new_column

        return data

    def verify_duplicate(self, data: pd.DataFrame, sheet_name: str, column_name: str):

        if column_name not in data.columns:
            return data

        duplicated = data[column_name][data[column_name].duplicated(keep=False)]    
        
        data = data.drop_duplicates(subset=column_name, keep="first")

        for name in duplicated.unique():
            if "#" in name:
                continue
            self.warning_message(
                sheet_name,
                f"{column_name.capitalize()} {name} duplicado na tabela. Considerado apenas o primeiro."
            )

        return data

    def after_verify_duplicate(self, data: pd.DataFrame, column_name: str):

        new_column = []
        for _, row in data.iterrows():
            if "#" in row[column_name]:
                new_column.append(0)
            else:
                new_column.append(row[column_name])

        data[column_name] = new_column

        return data


    def create_disp_m(self, professional_rule: pd.DataFrame):
        header = [ x.strip() for x in professional_rule.columns ]
        values = professional_rule.values

        if 'profissional' not in header:
            self.missing_column("RegraProfissional", "profissional")

        if 'tipo' not in header:
            self.missing_column("RegraProfissional", "tipo")

        if 'horas_semana' not in header:
            self.missing_column("RegraProfissional", "horas_semana")

        professional_index = np.arange(values.shape[0])
        professional_map = dict()
        disp_m = np.zeros(shape=(values.shape[0]))

        for i, row in enumerate(values):
            professional_map[i] = row[0]

            disp_m[i] = row[2]

            if not disp_m[i] or not isinstance(disp_m[i], (float, int)):
                self.warning_message(
                    "RegraProfissional",
                    f"Profissional {professional_map[i]} sem horário de disponibilidade. Não será alocado."
                )

        return professional_index, professional_map, disp_m

    def create_competence_m_p(self, professional_rule: pd.DataFrame, patient_info: pd.DataFrame):
        professional_header = [ x.strip() for x in professional_rule.columns ]
        professional_values = professional_rule.values
        patient_header = [ x.strip() for x in patient_info.columns ]
        patient_values = patient_info.values

        if 'infantil' not in professional_header:
            self.missing_column("RegraProfissional", "infantil")

        if 'adolescente' not in professional_header:
            self.missing_column("RegraProfissional", "adolescente")

        if 'adulto' not in professional_header:
            self.missing_column("RegraProfissional", "adulto")

        if 'paciente' not in patient_header:
            self.missing_column("IdadePaciente", "paciente")

        if 'idade' not in patient_header:
            self.missing_column("IdadePaciente", "idade")

        patient_index = np.arange(patient_values.shape[0])
        patient_map = dict()
        competence_m_p = np.zeros(shape=(professional_values.shape[0], patient_values.shape[0]))

        for pa, patient_row in enumerate(patient_values):
            patient_map[pa] = patient_row[0]
            patient_age = patient_row[1]

            if not patient_row[0]:
                self.error_missing_value(
                    "IdadePaciente",
                    f"Paciente sem nome cadastratado."
                )

            if not isinstance(patient_age, (int, float)):
                self.error_missing_value(
                    "IdadePaciente",
                    f"Paciente {patient_row[0]} sem idade cadastratada."
                )

            for pr, professional_row in enumerate(professional_values):

                if ((int(patient_age) < 12) and (professional_row[3] != 0)) or \
                    ((12 <= int(patient_age) < 18) and (professional_row[4] != 0)) or \
                    ((18 <= int(patient_age)) and (professional_row[5] != 0)):

                    competence_m_p[pr][pa] = 1

        return patient_index, patient_map, competence_m_p

    def create_local_m_l(self, local_professional: pd.DataFrame):
        local_header = [x.strip() for x in local_professional.columns]
        local_values = local_professional.values

        if 'profissional' not in local_header:
            self.missing_column("LocalProfissional", "profissional")

        if 'virtual_epsi' not in local_header:
            self.missing_column("LocalProfissional", "virtual_epsi")

        local_index = np.arange(len(local_header[1:]))

        local_header_with_virtual = np.array(['virtual_epsi'])
        local_header_with_virtual = np.concatenate((local_header_with_virtual,local_header[2:]))
        local_names = {i: local_name for i, local_name in enumerate(local_header_with_virtual)}

        local_m_l = np.zeros(shape=(local_values.shape[0], (local_values.shape[1] - 1)))

        for pr, row in enumerate(local_values):

            if not row[0]:
                self.error_missing_value("LocalProfissional", f"Profissional sem nome cadastratado.")

            for l, col in enumerate(local_header[1:]):
                local_m_l[pr][l] = 1 if row[(l + 1)] != 0 else 0

        return local_index, local_names, local_m_l

    # ===================================================
    def create_local_p_l_d(self, local_patient: pd.DataFrame, patient_info: pd.DataFrame):
    # ===================================================
        local_header = [ x.strip() for x in local_patient.columns ]
        local_values = local_patient.values
        patient_header = [ x.strip() for x in patient_info.columns ]
        patient_values = patient_info.values

        if 'paciente' not in local_header:
            self.missing_column("LocalPaciente", "paciente")

        if 'dia_semana' not in local_header:
            self.missing_column("LocalPaciente", "dia_semana")

        if 'virtual_epsi' not in local_header:
            self.missing_column("LocalPaciente", "virtual_epsi")

    # ===================================================
        if 'paciente' not in patient_header:
            self.missing_column("IdadePaciente", "paciente")

        if 'idade' not in patient_header:
            self.missing_column("IdadePaciente", "idade")
    # ===================================================

        if (len(local_values) % WEEK_SIZE) != 0:
            self.error_missing_value("LocalPaciente", f"É necessário que exista um dia da semana para cada paciente.")

        local_p_l_d = np.zeros(shape=(int(local_values.shape[0] / WEEK_SIZE), (local_values.shape[1] - 2), WEEK_SIZE))

        disponible = dict()
        patient_name = str()
        for pa, row in enumerate(local_values):
            if row[0]:
                patient_name = row[0]
                disponible[patient_name] = list()

            patient_index = pa // WEEK_SIZE
            d = pa % WEEK_SIZE

            disp_in_week = False

            for l, col in enumerate(local_header[2:]):

                if row[(l + 2)] != 0:
                    disp_in_week = True

                local_p_l_d[patient_index][l][d] = 1 if row[(l + 2)] != 0 else 0

                # ===================================================
                if (l == 0) and (int(patient_values[patient_index][1]) < 12):
                    local_p_l_d[patient_index][l][d] = 0
                # ===================================================

            disponible[patient_name].append(disp_in_week)

        for pa, disps in disponible.items():
            if not any(disps):
                self.warning_message("LocalPaciente", f"O paciente {pa} não possui locais disponíveis. Não será alocado.")

        return local_p_l_d

    def create_dispon_p_d_h(self, dispon_patient: pd.DataFrame):
        dispon_header = [ x.strip() for x in dispon_patient.columns ]
        dispon_values = dispon_patient.values

        if 'paciente' not in dispon_header:
            self.missing_column("DisponPaciente", "paciente")

        if 'dia_semana' not in dispon_header:
            self.missing_column("DisponPaciente", "dia_semana")

        for i in range(8, 21):
            col = "hr_" + str(i)
            if col not in dispon_header:
                self.missing_column("DisponPaciente", "col")

        if (len(dispon_values) % WEEK_SIZE) != 0:
            self.error_missing_value("DisponPaciente", f"É necessário que exista um dia da semana para cada paciente.")

        hour_p_d_h = np.zeros(shape=(int(dispon_values.shape[0] / WEEK_SIZE), WEEK_SIZE, HOUR_PER_DAY))

        disponible = dict()
        patient_name = str()
        for pa, row in enumerate(dispon_values):
            if row[0]:
                patient_name = row[0]
                disponible[patient_name] = list()

            patient_index = pa // WEEK_SIZE
            d = pa % WEEK_SIZE

            disp_in_week = False

            for h, col in enumerate(dispon_header[2:]):

                if row[(h + 2)] != 0:
                    disp_in_week = True

                hour_p_d_h[patient_index][d][h] = 1 if row[(h + 2)] != 0 else 0

            disponible[patient_name].append(disp_in_week)

        for pa, disps in disponible.items():
            if not any(disps):
                self.warning_message("DisponPaciente", f"O paciente {pa} não possui horas disponíveis. Não será alocado.")

        return hour_p_d_h

    def create_dispon_m_d_h(self, dispon_professional: pd.DataFrame):
        dispon_header = [x.strip() for x in dispon_professional.columns]
        dispon_values = dispon_professional.values

        if 'profissional' not in dispon_header:
            self.missing_column("DisponProfissional", "profissional")

        if 'dia_semana' not in dispon_header:
            self.missing_column("DisponProfissional", "dia_semana")

        for i in range(8, 21):
            col = "hr_" + str(i)
            if col not in dispon_header:
                self.missing_column("DisponPaciente", "col")

        if (len(dispon_values) % WEEK_SIZE) != 0:
            self.error_missing_value("DisponProfissional", f"É necessário que exista um dia da semana para cada profissional.")

        hour_p_d_h = np.zeros(shape=(int(dispon_values.shape[0] / WEEK_SIZE), WEEK_SIZE, HOUR_PER_DAY))

        disponible = dict()
        professional_name = str()
        for pr, row in enumerate(dispon_values):
            if row[0]:
                professional_name = row[0]
                disponible[professional_name] = list()

            professional_index = pr // WEEK_SIZE
            d = pr % WEEK_SIZE

            disp_in_week = False

            for h, col in enumerate(dispon_header[2:]):

                if row[(h + 2)] != 0:
                    disp_in_week = True

                hour_p_d_h[professional_index][d][h] = 1 if row[(h + 2)] != 0 else 0

            disponible[professional_name].append(disp_in_week)

        for pr, disps in disponible.items():
            if not any(disps):
                self.warning_message(
                    "DisponProfissional",
                    f"O profissional {pr} não possui horas disponíveis. Não será alocado."
                )

        return hour_p_d_h

    def missing_column(self, table: str, col: str):
        self.errors.append({
            "table": table,
            "type": "ERRO",
            "message": f"Coluna '{col}' não está presente na tabela."
        })

    def error_missing_value(self, table: str, message: str):
        self.errors.append({
            "table": table,
            "type": "ERRO",
            "message": message
        })

    def warning_message(self, table: str, message: str):
        self.errors.append({
            "table": table,
            "type": "AVISO",
            "message": message
        })