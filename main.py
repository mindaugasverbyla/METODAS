import sys
import sqlite3
import bcrypt
import requests
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QSystemTrayIcon,
    QHBoxLayout,
    QAbstractItemDelegate,
    QComboBox,
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon, QKeyEvent
from bs4 import BeautifulSoup
from gmail_client import GmailClient
import re


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed


def check_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode("utf-8"), stored_password)


def sukurti_duomenu_baze():

    with sqlite3.connect("metodas.db") as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS vartotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT NOT NULL,
            pavarde TEXT NOT NULL,
            prisijungimo_vardas TEXT NOT NULL UNIQUE,
            el_pastas TEXT,
            slaptazodis BLOB NOT NULL,
            prisiregistravimo_laikas TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ar_blokuotas BOOLEAN DEFAULT 0
        );
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS projektai (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            vartotojo_id INTEGER NOT NULL,
            pavadinimas TEXT NOT NULL,
            nuoroda TEXT,
            skriptas TEXT,
            ar_rodyti BOOLEAN DEFAULT 1,
            FOREIGN KEY(vartotojo_id) REFERENCES vartotojai(id)
        );
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS kriterijai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projekto_id INTEGER NOT NULL,
            pavadinimas TEXT NOT NULL,
            ar_teigiamas BOOLEAN DEFAULT 1,
            reiksme REAL NOT NULL,
            matavimo_vienetas TEXT NOT NULL,
            tipas TEXT NOT NULL,
            skriptas TEXT,
            FOREIGN KEY(projekto_id) REFERENCES projektai(id)
        );
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS objektai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projekto_id INTEGER NOT NULL,
            pavadinimas TEXT NOT NULL,
            nuoroda TEXT,
            aprasymas TEXT,
            pasirinktas BOOLEAN DEFAULT 1, 
            reiksmes TEXT, 
            reiksmes_skaiciavimui TEXT,           
            FOREIGN KEY(projekto_id) REFERENCES projektai(id)
        );
        """
        )

        cursor.execute(
            """
        DROP TABLE rezultatai;
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS rezultatai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projekto_id INTEGER NOT NULL,
            objekto_id INTEGER NOT NULL,
            reiksme_objekto REAL NOT NULL,
            kriterijaus_id INTEGER NOT NULL,
            reiksme_kriterijus REAL NOT NULL,
            ar_teigiamas BOOLEAN DEFAULT 1, 
            reiksme REAL NOT NULL,
            FOREIGN KEY(projekto_id) REFERENCES projektai(id),
            FOREIGN KEY(objekto_id) REFERENCES objektai(id),
            FOREIGN KEY(kriterijaus_id) REFERENCES kriterijai(id)
        );
        """
        )


class PagrindinisLangas(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("METODAS: Pagrindinis langas")
        self.setGeometry(100, 100, 600, 400)
        self.centerWindow()
        self.showFullScreen()
        self.tray_icon = QSystemTrayIcon(QIcon("metodas.png"), self)
        self.tray_icon.setToolTip("Metodas")
        self.vartotojo_id = 0
        self.projekto_id = 0
        self.projekto_eil = 0
        self.kriterijaus_id = 0
        self.kriterijaus_eil = 0
        self.objekto_id = 0
        self.objekto_eil = 0
        self.viso_projektu = 0
        self.viso_kriteriju = 0
        self.viso_objektu = 0
        self.settings = QSettings("Metodas", "Metodas")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        self.table_projektai = QTableWidget()
        self.table_projektai.setSelectionMode(self.table_projektai.SingleSelection)
        self.table_projektai.setColumnCount(4)
        self.table_projektai.setColumnWidth(1, 500)
        self.table_projektai.setColumnWidth(2, 500)
        self.table_projektai.setColumnWidth(3, 500)
        self.table_projektai.setSelectionMode(self.table_projektai.SingleSelection)
        self.table_projektai.itemSelectionChanged.connect(self.pasirinkti_projekta)
        self.table_projektai.setHorizontalHeaderLabels(
            ["Id", "Projektas", "Svetainės nuoroda", "Skriptas svetainės nuskaitymui"]
        )
        self.gauti_projekto_eilutes()

        layout.addWidget(self.table_projektai)

        self.projektas_horiz = QHBoxLayout()

        self.add_projektas = QPushButton("Pridėti projektą")
        self.add_projektas.clicked.connect(self.prideti_projekta)
        self.projektas_horiz.addWidget(self.add_projektas)

        self.save_projektas = QPushButton("Saugoti projektus")
        self.save_projektas.clicked.connect(self.saugoti_projektus)
        self.save_projektas.setDisabled(True)
        self.projektas_horiz.addWidget(self.save_projektas)

        self.del_projektas = QPushButton("Trinti projektą")
        self.del_projektas.clicked.connect(self.trinti_projekta)
        self.del_projektas.setDisabled(True)
        self.projektas_horiz.addWidget(self.del_projektas)

        layout.addLayout(self.projektas_horiz)

        self.table_kriterijai = QTableWidget()
        self.table_kriterijai.setColumnCount(7)
        self.table_kriterijai.setColumnWidth(1, 500)
        self.table_kriterijai.setSelectionMode(self.table_kriterijai.SingleSelection)
        self.table_kriterijai.itemSelectionChanged.connect(self.pasirinkti_kriteriju)
        self.table_kriterijai.setHorizontalHeaderLabels(
            [
                "Id",
                "Kriterijaus pavadinimas",
                "Reikšmė",
                "Ar teigiamas?",
                "Matavimo vienetas",
                "Tipas",
                "Reikšmės pozicija",
            ]
        )
        self.gauti_kriteriju_eilutes()

        layout.addWidget(self.table_kriterijai)

        self.kriterijai_horiz = QHBoxLayout()

        self.add_kriterijus = QPushButton("Pridėti kriterijų")
        self.add_kriterijus.clicked.connect(self.prideti_kriteriju)
        self.add_kriterijus.setDisabled(True)
        self.kriterijai_horiz.addWidget(self.add_kriterijus)

        self.save_kriterijus = QPushButton("Saugoti kriterijus")
        self.save_kriterijus.clicked.connect(self.saugoti_kriteriju)
        self.save_kriterijus.setDisabled(True)
        self.kriterijai_horiz.addWidget(self.save_kriterijus)

        self.del_kriterijus = QPushButton("Trinti kriterijų")
        self.del_kriterijus.clicked.connect(self.trinti_kriteriju)
        self.del_kriterijus.setDisabled(True)
        self.kriterijai_horiz.addWidget(self.del_kriterijus)

        layout.addLayout(self.kriterijai_horiz)

        self.table_objektai = QTableWidget()
        self.table_objektai.setColumnCount(4)
        self.table_objektai.setColumnWidth(1, 300)
        self.table_objektai.setColumnWidth(2, 100)
        self.table_objektai.setColumnWidth(3, 100)
        self.table_objektai.setHorizontalHeaderLabels(
            ["Id", "Objekto pavadinimas", "Nuoroda", "Aprašymas"]
        )
        self.table_objektai.setSelectionMode(self.table_objektai.SingleSelection)
        self.table_objektai.itemSelectionChanged.connect(self.pasirinkti_objekta)
        self.gauti_kriteriju_eilutes()

        layout.addWidget(self.table_objektai)

        self.objektai_horiz = QHBoxLayout()

        self.add_objektai = QPushButton("Gauti objektus")
        self.add_objektai.clicked.connect(self.gauti_objektus)
        self.add_objektai.setDisabled(True)
        self.objektai_horiz.addWidget(self.add_objektai)

        self.save_objektai = QPushButton("Saugoti objektus")
        self.save_objektai.clicked.connect(self.saugoti_objektus)
        self.save_objektai.setDisabled(True)
        self.objektai_horiz.addWidget(self.save_objektai)

        self.del_objektai = QPushButton("Trinti objektus")
        self.del_objektai.clicked.connect(self.trinti_objektus)
        self.del_objektai.setDisabled(True)
        self.objektai_horiz.addWidget(self.del_objektai)

        self.gauti_objektu_eilutes()

        layout.addLayout(self.objektai_horiz)

        self.table_rezultatai = QTableWidget()
        self.table_rezultatai.setColumnCount(4)
        self.table_rezultatai.setHorizontalHeaderLabels(["Id", "Projektas"])

        layout.addWidget(self.table_rezultatai)

        self.add_rezultatai = QPushButton("Rezultatai")
        self.add_rezultatai.clicked.connect(self.gauti_rezultatus)
        self.add_rezultatai.setDisabled(True)
        layout.addWidget(self.add_rezultatai)

        uzdarymo_mygtukas = QPushButton("Baigti darbą")
        uzdarymo_mygtukas.clicked.connect(self.close)

        layout.addWidget(uzdarymo_mygtukas)
        central_widget.setLayout(layout)

    def pasirinkti_projekta(self):
        selected_items = self.table_projektai.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            # projekto_id = self.table_projektai.item(row, 0).text()
            self.projekto_id = int(self.table_projektai.item(row, 0).text())
            self.projekto_eil = row
            self.add_kriterijus.setEnabled(True)
            self.add_objektai.setEnabled(True)
            self.add_rezultatai.setEnabled(True)
            self.save_projektas.setEnabled(True)
            self.del_projektas.setEnabled(True)
            self.gauti_kriteriju_eilutes()
            self.gauti_objektu_eilutes()
            # QMessageBox.information(self, "Projektas", f"ID: {self.projekto_id}\nEil: {self.projekto_eil}")
        else:
            self.add_kriterijus.setDisabled(True)
            self.add_objektai.setDisabled(True)
            self.add_rezultatai.setDisabled(True)
            self.save_projektas.setDisabled(True)
            self.del_projektas.setDisabled(True)
            self.projekto_id = 0
            self.projekto_eil = 0
            self.gauti_objektu_eilutes()
            # QMessageBox.information(self, "Projektas", "Projektas nepasirinktas")

    def pasirinkti_kriteriju(self):
        selected_items = self.table_kriterijai.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            # projekto_id = self.table_projektai.item(row, 0).text()
            self.kriterijaus_id = int(self.table_kriterijai.item(row, 0).text())
            self.kriterijaus_eil = row
            self.save_kriterijus.setEnabled(True)
            self.del_kriterijus.setEnabled(True)
            # QMessageBox.information(self, "Projektas", f"ID: {self.projekto_id}\nEil: {self.projekto_eil}")
        else:
            self.kriterijaus_id = 0
            self.kriterijaus_eil = 0
            self.save_kriterijus.setDisabled(True)
            self.del_kriterijus.setDisabled(True)
            # QMessageBox.information(self, "Projektas", "Projektas nepasirinktas")

    def pasirinkti_objekta(self):
        selected_items = self.table_objektai.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            self.objekto_id = int(self.table_objektai.item(row, 0).text())
            self.objekto_eil = row
            self.save_objektai.setEnabled(True)
            self.del_objektai.setEnabled(True)
            # QMessageBox.information(self, "Projektas", f"ID: {self.projekto_id}\nEil: {self.projekto_eil}")
        else:
            self.objekto_id = 0
            self.objekto_eil = 0
            self.save_objektai.setDisabled(True)
            self.del_objektai.setDisabled(True)
            # QMessageBox.information(self, "Projektas", "Projektas nepasirinktas")

    def prideti_projekta(self):
        self.vartotojo_id = self.settings.value("vartotojo_id", 0)
        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            try:
                c.execute(
                    """
                    INSERT INTO projektai (vartotojo_id, pavadinimas, nuoroda, skriptas, ar_rodyti)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (self.vartotojo_id, "Naujas projektas", "", "", 1),
                )
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Klaida", "Nepavyko pridėti projekto")
        self.gauti_projekto_eilutes()

    def prideti_kriteriju(self):
        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            try:
                c.execute(
                    """
                    INSERT INTO kriterijai (projekto_id, pavadinimas, ar_teigiamas, reiksme, matavimo_vienetas, tipas, skriptas)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.projekto_id,
                        "Kriterijus (pvz. Kaina)",
                        True,
                        1,
                        "Mat. vnt.(pvz. Eur)",
                        "Auto",
                        "",
                    ),
                )

            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Klaida", "Nepavyko pridėti kriterijaus")

        self.gauti_kriteriju_eilutes()

    def gauti_projekto_eilutes(self):
        self.vartotojo_id = self.settings.value("vartotojo_id", 0)

        while self.table_projektai.rowCount() > 0:
            self.table_projektai.removeRow(0)

        self.viso_projektu = 0

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            projektai = c.execute(
                "SELECT * FROM projektai WHERE vartotojo_id = '"
                + str(self.vartotojo_id)
                + "' and ar_rodyti = 1"
            ).fetchall()

        eilute = 0
        for projektas in projektai:

            self.table_projektai.insertRow(eilute)

            item_id = QTableWidgetItem(str(projektas[0]))
            item_id.setFlags(item_id.flags() & Qt.ItemIsEditable)
            self.table_projektai.setItem(eilute, 0, item_id)

            item_name = QTableWidgetItem(projektas[2])
            item_name.setFlags(item_name.flags() | Qt.ItemIsEditable)
            self.table_projektai.setItem(eilute, 1, item_name)

            item_url = QTableWidgetItem(projektas[3])
            item_url.setFlags(item_name.flags() | Qt.ItemIsEditable)
            self.table_projektai.setItem(eilute, 2, item_url)

            item_scr = QTableWidgetItem(projektas[4])
            item_scr.setFlags(item_name.flags() | Qt.ItemIsEditable)
            self.table_projektai.setItem(eilute, 3, item_scr)

            eilute += 1

        self.viso_projektu = eilute

    def gauti_kriteriju_eilutes(self):
        while self.table_kriterijai.rowCount() > 0:
            self.table_kriterijai.removeRow(0)

        self.viso_kriteriju = 0

        if not (self.projekto_id == 0):

            with sqlite3.connect("metodas.db") as conn:
                c = conn.cursor()
                self.kriterijai = c.execute(
                    "SELECT * FROM kriterijai WHERE projekto_id = '"
                    + str(self.projekto_id)
                    + "'"
                ).fetchall()

                eilute = 0

                for kriterijus in self.kriterijai:

                    self.table_kriterijai.insertRow(eilute)

                    item_id = QTableWidgetItem(str(kriterijus[0]))
                    item_id.setFlags(item_id.flags() & Qt.ItemIsEditable)
                    self.table_kriterijai.setItem(eilute, 0, item_id)

                    item_name = QTableWidgetItem(kriterijus[2])
                    item_name.setFlags(item_name.flags() | Qt.ItemIsEditable)
                    self.table_kriterijai.setItem(eilute, 1, item_name)

                    item_value = QTableWidgetItem(str(kriterijus[4]))
                    item_value.setFlags(item_name.flags() | Qt.ItemIsEditable)
                    self.table_kriterijai.setItem(eilute, 2, item_value)

                    tipas_teigiamas_neigiamas = QComboBox()
                    tipas_teigiamas_neigiamas.addItems(["Teigiamas", "Neigiamas"])
                    if kriterijus[3] == 1:
                        tipas_teigiamas_neigiamas.setCurrentText("Teigiamas")
                    else:
                        tipas_teigiamas_neigiamas.setCurrentText("Neigiamas")

                    self.table_kriterijai.setCellWidget(
                        eilute, 3, tipas_teigiamas_neigiamas
                    )

                    item_mat = QTableWidgetItem(str(kriterijus[5]))
                    item_mat.setFlags(item_name.flags() | Qt.ItemIsEditable)
                    self.table_kriterijai.setItem(eilute, 4, item_mat)

                    tipas_combo = QComboBox()
                    tipas_combo.addItems(["Auto", "Įvedamas"])
                    tipas_combo.setCurrentText(kriterijus[6])
                    self.table_kriterijai.setCellWidget(eilute, 5, tipas_combo)

                    item_skript = QTableWidgetItem(str(kriterijus[7]))
                    item_skript.setFlags(item_name.flags() | Qt.ItemIsEditable)
                    self.table_kriterijai.setItem(eilute, 6, item_skript)

                    eilute += 1

                self.viso_kriteriju = eilute

    def gauti_objektu_eilutes(self):

        while self.table_objektai.rowCount() > 0:
            self.table_objektai.removeRow(0)

        self.table_objektai.setColumnCount(5 + self.viso_kriteriju)

        labels = [
            "Id",
            "Objekto pavadinimas",
            "Nuoroda",
            "Aprašymas",
            "Ar pasirinktas?",
        ]

        self.table_objektai.setHorizontalHeaderLabels(labels)

        self.viso_objektu = 0

        if not (self.projekto_id == 0):

            with sqlite3.connect("metodas.db") as conn:
                c = conn.cursor()
                self.kriterijai = c.execute(
                    "SELECT * FROM kriterijai WHERE projekto_id = '"
                    + str(self.projekto_id)
                    + "'"
                ).fetchall()
                for kriterijus in self.kriterijai:
                    labels.append(kriterijus[2] + ", " + kriterijus[5])

                self.table_objektai.setHorizontalHeaderLabels(labels)
                self.table_objektai.setSelectionMode(
                    self.table_objektai.SingleSelection
                )
                self.table_objektai.itemSelectionChanged.connect(
                    self.pasirinkti_objekta
                )

                self.objektai = c.execute(
                    "SELECT * FROM objektai WHERE projekto_id = '"
                    + str(self.projekto_id)
                    + "'"
                ).fetchall()

                eilute = 0

                for objektas in self.objektai:

                    self.table_objektai.insertRow(eilute)

                    item_id = QTableWidgetItem(str(objektas[0]))
                    item_id.setFlags(item_id.flags() & Qt.ItemIsEditable)
                    self.table_objektai.setItem(eilute, 0, item_id)

                    item_name = QTableWidgetItem(objektas[2])
                    item_name.setFlags(item_name.flags() & Qt.ItemIsEditable)
                    self.table_objektai.setItem(eilute, 1, item_name)

                    item_url = QTableWidgetItem(str(objektas[3]))
                    item_url.setFlags(item_url.flags() | Qt.ItemIsEditable)
                    self.table_objektai.setItem(eilute, 2, item_url)

                    item_note = QTableWidgetItem(str(objektas[4]))
                    item_note.setFlags(item_note.flags() | Qt.ItemIsEditable)
                    self.table_objektai.setItem(eilute, 3, item_note)

                    pasirinktas = QComboBox()
                    pasirinktas.addItems(["Pasirinktas", "Nepasirinktas"])
                    if objektas[5] == 1:
                        pasirinktas.setCurrentText("Pasirinktas")
                    else:
                        pasirinktas.setCurrentText("Nepasirinktas")

                    self.table_objektai.setCellWidget(eilute, 4, pasirinktas)

                    reiksmes = str(objektas[7])
                    reiksmes = reiksmes.split("|")
                    if len(reiksmes) > 1:
                        reiksmes_nr = 0
                        for kriterijus in self.kriterijai:
                            self.table_objektai.setColumnWidth(5 + reiksmes_nr, 200)
                            if kriterijus[7] == "":
                                item_val = QTableWidgetItem(
                                    re.sub(r"[^0-9.]", "", str(reiksmes[reiksmes_nr]))
                                )
                                item_val.setFlags(item_val.flags() | Qt.ItemIsEditable)
                                item_val.setTextAlignment(Qt.AlignCenter)
                                self.table_objektai.setItem(
                                    eilute, 5 + reiksmes_nr, item_val
                                )
                            else:
                                item_val = QTableWidgetItem(
                                    re.sub(r"[^0-9.]", "", str(reiksmes[reiksmes_nr]))
                                )

                                item_val.setFlags(item_val.flags() | Qt.ItemIsEditable)
                                item_val.setTextAlignment(Qt.AlignCenter)
                                self.table_objektai.setItem(
                                    eilute, 5 + reiksmes_nr, item_val
                                )

                            reiksmes_nr += 1
                    else:
                        reiksmes = str(objektas[6])
                        reiksmes = reiksmes.split("|")
                        if len(reiksmes) > 1:
                            reiksmes_nr = 0
                            for kriterijus in self.kriterijai:
                                self.table_objektai.setColumnWidth(5 + reiksmes_nr, 200)
                                if kriterijus[7] == "":
                                    item_val = QTableWidgetItem(str(0.0))
                                    item_val.setFlags(
                                        item_val.flags() | Qt.ItemIsEditable
                                    )
                                    item_val.setTextAlignment(Qt.AlignCenter)
                                    self.table_objektai.setItem(
                                        eilute, 5 + reiksmes_nr, item_val
                                    )
                                else:
                                    item_val = QTableWidgetItem(
                                        re.sub(
                                            r"[^0-9.]",
                                            "",
                                            str(reiksmes[int(kriterijus[7])]),
                                        )
                                    )

                                    item_val.setFlags(
                                        item_val.flags() | Qt.ItemIsEditable
                                    )
                                    item_val.setTextAlignment(Qt.AlignCenter)
                                    self.table_objektai.setItem(
                                        eilute, 5 + reiksmes_nr, item_val
                                    )

                                reiksmes_nr += 1

                    eilute += 1

            self.viso_objektu = eilute

    def saugoti_projektus(self):
        editor = self.table_projektai.focusWidget()
        if editor:
            enter_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
            QApplication.postEvent(editor, enter_event)

        self.table_projektai.closeEditor(editor, QAbstractItemDelegate.SubmitModelCache)
        self.table_projektai.clearFocus()

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            for eilute in range(0, self.viso_projektu):
                c.execute(
                    "UPDATE projektai SET pavadinimas='"
                    + self.table_projektai.item(eilute, 1).text()
                    + "', nuoroda='"
                    + self.table_projektai.item(eilute, 2).text()
                    + "', skriptas='"
                    + self.table_projektai.item(eilute, 3).text()
                    + "' WHERE id = '"
                    + self.table_projektai.item(eilute, 0).text()
                    + "'"
                )

        self.gauti_projekto_eilutes()

    def saugoti_kriteriju(self):

        response = QMessageBox.question(
            self,
            "Patvirtinimas",
            "Ar tikrai norite iš naujo ištraukti duomenis? Išsitrins esami duomenys!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if response == QMessageBox.No:
            return

        editor = self.table_kriterijai.focusWidget()
        if editor:
            enter_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
            QApplication.postEvent(editor, enter_event)

        self.table_kriterijai.closeEditor(
            editor, QAbstractItemDelegate.SubmitModelCache
        )
        self.table_kriterijai.clearFocus()

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()

            for eilute in range(0, self.viso_kriteriju):
                ar_teig = self.table_kriterijai.cellWidget(eilute, 3).currentText()
                if ar_teig == "Teigiamas":
                    ar_teig_value = str(1)
                else:
                    ar_teig_value = str(0)

                c.execute(
                    "UPDATE kriterijai SET pavadinimas='"
                    + self.table_kriterijai.item(eilute, 1).text()
                    + "', reiksme="
                    + self.table_kriterijai.item(eilute, 2).text()
                    + ", ar_teigiamas = "
                    + ar_teig_value
                    + ", matavimo_vienetas='"
                    + self.table_kriterijai.item(eilute, 4).text()
                    + "', tipas='"
                    + self.table_kriterijai.cellWidget(eilute, 5).currentText()
                    + "', skriptas='"
                    + self.table_kriterijai.item(eilute, 6).text()
                    + "'  WHERE id = '"
                    + self.table_kriterijai.item(eilute, 0).text()
                    + "'"
                )

        self.gauti_kriteriju_eilutes()

    def saugoti_objektus(self):

        editor = self.table_objektai.focusWidget()
        if editor:
            enter_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
            QApplication.postEvent(editor, enter_event)

        self.table_objektai.closeEditor(editor, QAbstractItemDelegate.SubmitModelCache)
        self.table_objektai.clearFocus()

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()

            for eilute in range(0, self.viso_objektu):
                ar_prisk = self.table_objektai.cellWidget(eilute, 4).currentText()
                if ar_prisk == "Pasirinktas":
                    ar_prisk = str(1)
                else:
                    ar_prisk = str(0)

                reiksmes_skaiciavimui = ""
                for krit_nr in range(0, self.viso_kriteriju):
                    reiksmes_skaiciavimui += (
                        self.table_objektai.item(eilute, 5 + krit_nr).text() + "|"
                    )

                c.execute(
                    "UPDATE objektai SET pavadinimas = '"
                    + self.table_objektai.item(eilute, 1).text()
                    + "', nuoroda = '"
                    + self.table_objektai.item(eilute, 2).text()
                    + "', aprasymas = '"
                    + self.table_objektai.item(eilute, 3).text()
                    + "', pasirinktas = "
                    + ar_prisk
                    + ", reiksmes_skaiciavimui = '"
                    + str(reiksmes_skaiciavimui)
                    + "' WHERE id = '"
                    + self.table_objektai.item(eilute, 0).text()
                    + "'"
                )

        self.gauti_kriteriju_eilutes()

    def gauti_rezultatus(self):
        response = QMessageBox.question(
            self,
            "Patvirtinimas",
            "Visi duomenys teisingi ir norite skaičiuoti?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if response == QMessageBox.No:
            return

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM rezultatai WHERE projekto_id = '"
                + str(self.projekto_id)
                + "'"
            )
            self.kriterijai = c.execute(
                "SELECT * FROM kriterijai WHERE projekto_id = '"
                + str(self.projekto_id)
                + "'"
            ).fetchall()
            self.objektai = c.execute(
                "SELECT * FROM objektai WHERE pasirinktas = 1 AND projekto_id = '"
                + str(self.projekto_id)
                + "'"
            ).fetchall()
            krit_nr = 0
            for kriterijus in self.kriterijai:
                for objektas in self.objektai:

                    objekto_reiksmes = str(objektas[7])
                    objekto_reiksmes = objekto_reiksmes.split("|")
                    objekto_reiksme = objekto_reiksmes[krit_nr]

                    c.execute(
                        """
                    INSERT INTO rezultatai (projekto_id, objekto_id, reiksme_objekto, kriterijaus_id, reiksme_kriterijus, ar_teigiamas, reiksme)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            str(self.projekto_id),
                            str(objektas[0]),
                            str(objekto_reiksme),
                            str(kriterijus[0]),
                            str(kriterijus[4]),
                            str(kriterijus[3]),
                            str(self.projekto_id),
                        ),
                    )

                krit_nr += 1

            c.execute(
                """
                      SELECT * FROM rezultatai 
                      LEFT OUTER JOIN objektai ON objektai.id = rezultatai.objekto_id
                      LEFT OUTER JOIN kriterijai ON kriterijai.id = rezultatai.kriterijaus_id
                      WHERE rezultatai.projekto_id = ?
                      """,
                (str(self.projekto_id)),
            )
            eilutes = c.fetchall()

            stulpeliu_pavadinimai = [description[0] for description in c.description]

            self.table_rezultatai.setRowCount(len(eilutes))
            self.table_rezultatai.setColumnCount(len(stulpeliu_pavadinimai))
            self.table_rezultatai.setHorizontalHeaderLabels(stulpeliu_pavadinimai)

            for eilutes_indeksas, eilute in enumerate(eilutes):
                for stulpelio_indeksas, reiksme in enumerate(eilute):
                    self.table_rezultatai.setItem(
                        eilutes_indeksas,
                        stulpelio_indeksas,
                        QTableWidgetItem(str(reiksme)),
                    )

    def trinti_projekta(self):

        response = QMessageBox.question(
            self,
            "Patvirtinimas",
            "Ar tikrai norite trinti projektą? Išsitrins esami duomenys!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if response == QMessageBox.No:
            return

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM projektai WHERE id = '" + str(self.projekto_id) + "'"
            )
            c.execute(
                "DELETE FROM kriterijai WHERE projekto_id = '"
                + str(self.projekto_id)
                + "'"
            )
            c.execute(
                "DELETE FROM objektai WHERE projekto_id = '"
                + str(self.projekto_id)
                + "'"
            )

        self.gauti_projekto_eilutes()

    def trinti_kriteriju(self):
        response = QMessageBox.question(
            self,
            "Patvirtinimas",
            "Ar tikrai norite trinti esamą kriterijų? Išsitrins esami duomenys!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if response == QMessageBox.No:
            return

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM kriterijai WHERE id = '" + str(self.kriterijaus_id) + "'"
            )
        self.gauti_kriteriju_eilutes()

    def trinti_objektus(self):
        response = QMessageBox.question(
            self,
            "Patvirtinimas",
            "Ar tikrai norite trinti objektus? Išsitrins visi šio projekto objektai!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if response == QMessageBox.No:
            return

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM objektai WHERE projekto_id = '"
                + str(self.projekto_id)
                + "'"
            )
        self.gauti_objektu_eilutes()

    def centerWindow(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def gauti_objektus(self):

        response = QMessageBox.question(
            self,
            "Patvirtinimas",
            "Ar tikrai norite iš naujo traukti objektus? Išsitrins visi šio projekto objektai!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if response == QMessageBox.No:
            return

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM objektai WHERE projekto_id = '"
                + str(self.projekto_id)
                + "'"
            )
            projektas = c.execute(
                "SELECT * FROM projektai WHERE id = '"
                + str(self.projekto_id)
                + "' and vartotojo_id = '"
                + str(self.vartotojo_id)
                + "' and ar_rodyti = 1"
            ).fetchone()

            obj_url_pre = projektas[3]
            obj_url_pre = obj_url_pre.split("|")

            if len(obj_url_pre) == 1:
                obj_url = obj_url_pre[0]
                obj_url_from = 0
                obj_url_to = 1
                obj_url_template = projektas[4]
            elif len(obj_url_pre) == 4:
                obj_url = obj_url_pre[0]
                obj_url_from = int(obj_url_pre[1])
                obj_url_to = int(obj_url_pre[2])
                obj_url_template = projektas[4]
            else:
                obj_url = ""
                obj_url_from = 1
                obj_url_to = 0
                obj_url_template = projektas[4]

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, kaip Gecko) Version/17.3 Safari/605.1.15"
            }

            for eilute in range(obj_url_from, obj_url_to):

                if len(obj_url_pre) == 1:
                    obj_url_ready = obj_url
                elif len(obj_url_pre) == 4:
                    obj_url_ready = obj_url.replace("{psl}", str(eilute))
                else:
                    obj_url_ready = obj_url

                response = requests.get(obj_url_ready, headers=headers)
                if response.status_code != 200:
                    QMessageBox.warning(
                        self,
                        "Klaida",
                        "Nepavyko gauti duomenų. Patikrinkite projekto nuorodą: "
                        + obj_url_ready
                        + " Statuso kodas: "
                        + str(response.status_code),
                    )
                    return None

                soup = BeautifulSoup(response.text, "html.parser")

                if obj_url_template == "brc-2025-02-14":

                    try:

                        cars = soup.find_all("div", class_="cars")

                        for car in cars:
                            link_tag = car.find("a", href=True)
                            if link_tag:
                                link = link_tag["href"]
                                header = link_tag.get_text(strip=True)

                            subtitle = car.find_next(
                                "p", class_="cars__subtitle"
                            ).text.strip()
                            parts = [part.strip() for part in subtitle.split("|")]

                            year = parts[0]
                            engine = parts[1]
                            engine = engine.replace(" Dyzelinas", "")
                            engine = engine.replace(" Benzinas", "")
                            transmission = parts[2]
                            mileage = parts[3]
                            mileage = mileage.replace(" km", "")
                            power = parts[4]
                            power = power.split(" kW (")
                            if len(power) == 1:
                                power = power[0]
                            else:
                                power = power[1].replace(" AG)", "")

                            price = car.find_next(
                                "div", class_="cars-price"
                            ).text.strip()
                            price = price.replace("€", "")
                            price = price.split(" ")
                            if len(price) == 1:
                                price = price[0]
                            else:
                                price = price[1]

                            c.execute(
                                """
                            INSERT INTO objektai (projekto_id, pavadinimas, nuoroda, aprasymas, pasirinktas, reiksmes) VALUES 
                            (?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    self.projekto_id,
                                    header,
                                    link,
                                    "",
                                    0,
                                    price
                                    + "|"
                                    + year
                                    + "|"
                                    + engine
                                    + "|"
                                    + transmission
                                    + "|"
                                    + mileage
                                    + "|"
                                    + power,
                                ),
                            )

                    except AttributeError:
                        QMessageBox.warning(
                            self,
                            "Klaida",
                            "Nepavyko rasti visų duomenų. Tikrinkite puslapio struktūrą.",
                        )
                        return None

                elif obj_url_template == "domoplius-2025-02-14":

                    try:

                        items = soup.find_all("div", class_="item")

                        for item in items:
                            link_tag = item.find("a", href=True)
                            link = link_tag["href"] if link_tag else "Nerasta"
                            img_tag = item.find_next("img")
                            header = (
                                img_tag["alt"]
                                if img_tag and "alt" in img_tag.attrs
                                else "Nerasta"
                            )

                            # Kaina
                            price_tag = item.find("div", class_="price").find("strong")
                            price = (
                                price_tag.get_text(strip=True)
                                if price_tag
                                else "Nerasta"
                            )

                            # Plotas
                            param_list = item.find("div", class_="param-list")
                            area = "Nerasta"
                            if param_list:
                                for span in param_list.find_all("span"):
                                    if "m²" in span.get_text():
                                        area = span.get_text(strip=True)

                            area = area.replace(" m²", "")
                            area = area.replace(" ", "")
                            price = price.replace(" €", "")
                            price = price.replace(" ", "")

                            c.execute(
                                """
                            INSERT INTO objektai (projekto_id, pavadinimas, nuoroda, aprasymas, pasirinktas, reiksmes) VALUES 
                            (?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    self.projekto_id,
                                    header,
                                    link,
                                    "",
                                    0,
                                    price + "|" + area,
                                ),
                            )

                    except AttributeError:
                        QMessageBox.warning(
                            self,
                            "Klaida",
                            "Nepavyko rasti visų duomenų. Tikrinkite puslapio struktūrą.",
                        )
                        return None

                elif obj_url_template == "tele2-2025-02-14":
                    try:

                        phones = soup.find_all(
                            "div", class_="dygg234 itemDetails hw-pricing"
                        )

                        for phone in phones:
                            name = phone.find("div", class_="tmd8yt8").text.strip()

                            monthly_price = phone.find(
                                "div", class_="m1viuceg"
                            ).text.strip()
                            monthly_amount, monthly_period = monthly_price.split("€")
                            monthly_amount = monthly_amount.strip()
                            monthly_period = monthly_period.strip()

                            initial_payment = (
                                phone.find("div", class_="ia2y6vc")
                                .find("span", class_="price")
                                .text.strip()
                            )
                            full_price = (
                                phone.find("div", class_="fsdaiaw")
                                .find("span", class_="price")
                                .text.strip()
                            )

                            link_tag = phone.find_next("a", class_="ltjbhnf")
                            if link_tag:
                                link = link_tag.get("href")
                                full_link = f"https://tele2.lt{link}"
                            else:
                                full_link = ""

                            monthly_amount = monthly_amount.replace(",", ".")
                            monthly_period = monthly_period.replace("/", "")
                            monthly_period = monthly_period.replace(" ", "")
                            monthly_period = monthly_period.replace("mėn.", "")
                            initial_payment = initial_payment.replace(" €", "")
                            full_price = full_price.split(" ")
                            full_price = full_price[0]
                            full_price = full_price.replace(",", ".")
                            full_price = full_price.replace("€", "")
                            full_price = full_price.split(".")
                            full_price = full_price[0]

                            c.execute(
                                """
                            INSERT INTO objektai (projekto_id, pavadinimas, nuoroda, aprasymas, pasirinktas, reiksmes) VALUES 
                            (?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    self.projekto_id,
                                    name,
                                    full_link,
                                    "",
                                    0,
                                    monthly_price
                                    + "|"
                                    + monthly_amount
                                    + "|"
                                    + monthly_period
                                    + "|"
                                    + initial_payment
                                    + "|"
                                    + full_price,
                                ),
                            )

                    except AttributeError:
                        QMessageBox.warning(
                            self,
                            "Klaida",
                            "Nepavyko rasti visų duomenų. Tikrinkite puslapio struktūrą.",
                        )
                        return None

                else:
                    QMessageBox.warning(
                        self,
                        "Klaida",
                        "Programoje nėra tinkamo skripto svetainės nuskaitymui",
                    )

        self.gauti_objektu_eilutes()


class RegistracijosLangas(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registracija")
        self.setGeometry(100, 100, 300, 300)
        self.centerWindow()

        layout = QVBoxLayout()

        self.vardas_input = QLineEdit(self)
        self.vardas_input.setPlaceholderText("Vardas")
        layout.addWidget(self.vardas_input)

        self.pavarde_input = QLineEdit(self)
        self.pavarde_input.setPlaceholderText("Pavardė")
        layout.addWidget(self.pavarde_input)

        self.elpastas_input = QLineEdit(self)
        self.elpastas_input.setPlaceholderText("El. paštas")
        layout.addWidget(self.elpastas_input)

        self.prisijungimo_vardas_input = QLineEdit(self)
        self.prisijungimo_vardas_input.setPlaceholderText("Prisijungimo vardas")
        layout.addWidget(self.prisijungimo_vardas_input)

        self.slaptazodis_input = QLineEdit(self)
        self.slaptazodis_input.setPlaceholderText("Slaptažodis")
        self.slaptazodis_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.slaptazodis_input)

        self.registracija = QPushButton("Registruotis")
        self.registracija.clicked.connect(self.registruoti)
        layout.addWidget(self.registracija)

        self.setLayout(layout)

    def registruoti(self):
        vardas = self.vardas_input.text()
        pavarde = self.pavarde_input.text()
        prisijungimo_vardas = self.prisijungimo_vardas_input.text()
        el_pastas = self.elpastas_input.text()
        slaptazodis = self.slaptazodis_input.text()

        if (
            not vardas
            or not pavarde
            or not el_pastas
            or not prisijungimo_vardas
            or not slaptazodis
        ):
            QMessageBox.warning(self, "Klaida", "Užpildykite visus laukus!")
            return

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            try:
                c.execute(
                    """
                    INSERT INTO vartotojai (vardas, pavarde, prisijungimo_vardas, el_pastas, slaptazodis)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        vardas,
                        pavarde,
                        prisijungimo_vardas,
                        el_pastas,
                        hash_password(slaptazodis),
                    ),
                )

                QMessageBox.information(self, "Pavyko", "Registracija sėkminga!")

            except sqlite3.IntegrityError:
                QMessageBox.warning(
                    self,
                    "Klaida",
                    "Toks prisijungimo vardas jau egzistuoja! Registracija nesėkminga!",
                )

            try:
                gmail_client = GmailClient()
                gmail_client.send_email(
                    to_email=el_pastas,
                    subject="Jūsų prisijungimo duomenys programoje METODAS",
                    content="Vardas: "
                    + vardas
                    + "\nPavardė: "
                    + pavarde
                    + "\nEl. paštas: "
                    + el_pastas
                    + "\nPrisijungimo vardas: "
                    + prisijungimo_vardas
                    + "\nSlaptažodis: "
                    + slaptazodis,
                )
                QMessageBox.information(
                    self,
                    "Gausite laišką",
                    "Jums Jūsų el. pašto adresu yra išsiųstas laiškas su prisijungimo parametrais",
                )
            except:
                QMessageBox.warning(
                    self,
                    "Klaida",
                    "Nepavyko išsiųsti laiško su prisijungimo duomenimis!",
                )

            self.close()

    def open_login(self):
        self.login_window = PrisijungimoLangas()
        self.login_window.show()

    def centerWindow(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())


class PrisijungimoLangas(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prisijungimas")
        self.setGeometry(100, 100, 300, 200)
        self.centerWindow()
        self.tray_icon = QSystemTrayIcon(QIcon("metodas.png"), self)
        self.settings = QSettings("Metodas", "Metodas")

        layout = QVBoxLayout()

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Prisijungimo vardas")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Slaptažodis")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("Prisijungti")
        self.login_button.clicked.connect(self.login)

        self.password_input.returnPressed.connect(self.login_button.click)

        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)

        self.register_button = QPushButton("Registruotis")
        self.close()
        self.register_button.clicked.connect(self.i_registracija)
        layout.addWidget(self.register_button)

        self.setLayout(layout)

    def centerWindow(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def login(self):
        prisijungimo_vardas = self.username_input.text()
        slaptazodis = self.password_input.text()

        with sqlite3.connect("metodas.db") as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM vartotojai WHERE prisijungimo_vardas = '"
                + prisijungimo_vardas
                + "'"
            )
            self.vartotojas = c.fetchone()

            try:
                self.settings.setValue("vartotojo_id", self.vartotojas[0])
            except:
                QMessageBox.warning(
                    self, "Klaida", "Nėra registruotų vartotojų. Registruokitės!"
                )

            if self.vartotojas and check_password(self.vartotojas[5], slaptazodis):

                self.pagrindinis_langas = PagrindinisLangas()
                self.pagrindinis_langas.show()
                self.close()
            else:
                QMessageBox.warning(
                    self, "Klaida", "Neteisingas prisijungimo vardas arba slaptažodis!"
                )

    def i_registracija(self):
        self.reg_window = RegistracijosLangas()
        self.reg_window.show()


if __name__ == "__main__":
    sukurti_duomenu_baze()
    app = QApplication(sys.argv)
    window = PrisijungimoLangas()
    window.show()
    sys.exit(app.exec_())
