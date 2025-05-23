import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageWin
import barcode
from barcode.writer import ImageWriter
import datetime
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import win32print
import win32ui
import win32con
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# --- DATABASE SETUP ---
conn = sqlite3.connect("etiquettes.db")
cursor = conn.cursor()

# Create tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS etiquettes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modele TEXT,
        pointure TEXT,
        nb_paire TEXT,
        date_reception TEXT,
        coloris TEXT,
        code TEXT UNIQUE,
        of TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        designation TEXT,
        coloris TEXT,
        pointure TEXT,
        nb_paire TEXT,
        date_reception TEXT,
        lieu_stockage TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sorties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        designation TEXT,
        coloris TEXT,
        pointure TEXT,
        nb_paire TEXT,
        date_sortie TEXT
    )
''')
conn.commit()

# Model and color mappings
MODELE_MAPPING = {
    "DCDP500": "01",
    "DCDP900": "02",
    "MW": "03",
    "GAS": "04"
}
COLORIS_MAPPING = {
    "410NOIR": "012",
    "L07A PINK": "025",
    "BLEU": "189",
    "Nougat": "962",
    "N07ablanc": "364",
    "N07a black": "146",
    "GR GRIS": "397"
}
REVERSE_MODELE_MAPPING = {v: k for k, v in MODELE_MAPPING.items()}
REVERSE_COLORIS_MAPPING = {v: k for k, v in COLORIS_MAPPING.items()}

# --- FUNCTIONS ---
def generer_code_barre(modele, pointure, nb_paire, date_reception, of, coloris, display=True):
    if not all([modele, pointure, nb_paire, date_reception, of, coloris]):
        if display:
            messagebox.showerror("Erreur 🚫", "Tous les champs sont obligatoires.")
        return None

    if modele not in MODELE_MAPPING:
        if display:
            messagebox.showerror("Erreur 🚫", f"Modèle invalide. Choisissez parmi {list(MODELE_MAPPING.keys())}.")
        return None

    if coloris not in COLORIS_MAPPING:
        if display:
            messagebox.showerror("Erreur 🚫", f"Coloris invalide. Choisissez parmi {list(COLORIS_MAPPING.keys())}.")
        return None

    try:
        datetime.datetime.strptime(date_reception, "%Y-%m-%d")
        int_pointure = int(pointure)
        int_nb_paire = int(nb_paire)
        if not (28 <= int_pointure <= 45):
            raise ValueError("Pointure doit être entre 28 et 45.")
        if not (1 <= int_nb_paire <= 99):
            raise ValueError("Nombre de paires doit être entre 1 et 99.")
    except ValueError as e:
        if display:
            messagebox.showerror("Erreur 🚫", f"Date (AAAA-MM-JJ), pointure ou nombre de paires invalide: {e}")
        return None

    modele_code = MODELE_MAPPING[modele]
    coloris_code = COLORIS_MAPPING[coloris]
    nb_paire_padded = f"{int_nb_paire:02d}"
    code = f"25{pointure}{nb_paire_padded}{modele_code}{coloris_code}"

    if display:
        code_var.set(code)

    CODE128 = barcode.get_barcode_class('code128')
    code_barre = CODE128(code, writer=ImageWriter())
    filename = code_barre.save(f"etiquette_code_{code}")

    if display:
        img = Image.open(filename).resize((300, 100))
        photo = ImageTk.PhotoImage(img)
        label_img_code.config(image=photo)
        label_img_code.image = photo
        label_img_code.filename = filename

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO etiquettes (modele, pointure, nb_paire, date_reception, coloris, code, of)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (modele, pointure, nb_paire, date_reception, coloris, code, of))
        conn.commit()
        return {'code': code, 'filename': filename, 'modele': modele, 'pointure': pointure, 'nb_paire': nb_paire, 'coloris': coloris, 'of': of, 'date_reception': date_reception}
    except Exception as e:
        if display:
            messagebox.showerror("Erreur 🚫", f"Erreur lors de l'enregistrement en base: {e}")
        return None

def imprimer_code_barre():
    if not hasattr(label_img_code, 'filename') or not code_var.get().strip():
        messagebox.showerror("Erreur 🚫", "Aucun code-barres généré.")
        return

    try:
        img = Image.open(label_img_code.filename).convert('RGB')
        printer_name = win32print.GetDefaultPrinter()
        hprinter = win32print.OpenPrinter(printer_name)
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        hdc.StartDoc('Barcode Print')
        hdc.StartPage()

        dib = ImageWin.Dib(img)
        printable_width = 300 * 2
        printable_height = 100 * 2
        dib.draw(hdc.GetHandleOutput(), (100, 100, 100 + printable_width, 100 + printable_height))

        hdc.TextOut(100, 50, f"Modèle: {entry_modele.get()} Nb de Paire: {entry_nb_paire.get()}")
        hdc.TextOut(100, 30, f"Pointure: {entry_pointure.get()} Coloris: {entry_coloris.get()}")

        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
        win32print.ClosePrinter(hprinter)
        messagebox.showinfo("Succès ✅", "Code-barres envoyé à l'imprimante.")
    except Exception as e:
        messagebox.showerror("Erreur 🚫", f"Erreur lors de l'impression: {e}")

def generer_pdf():
    code = code_var.get().strip()
    if not code or not hasattr(label_img_code, 'filename'):
        messagebox.showerror("Erreur 🚫", "Aucun code-barres généré.")
        return

    file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if not file_path:
        return

    c = canvas.Canvas(file_path, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, f"Modèle: {entry_modele.get()} Nb de Paire: {entry_nb_paire.get()}")
    c.drawString(100, 730, f"Pointure: {entry_pointure.get()}")
    c.drawString(100, 710, f"Coloris: {entry_coloris.get()}")
    c.drawString(100, 690, f"Date réception: {entry_date.get()}")
    c.drawString(100, 670, f"Ordre de fabrication: {entry_of.get()}")
    c.drawImage(label_img_code.filename, 100, 500, width=300, height=100)
    c.showPage()
    c.save()
    messagebox.showinfo("Succès ✅", f"PDF sauvegardé sous {file_path}")

def generer_multi_codes():
    dialog = tk.Toplevel(root)
    dialog.title("Génération Multiple")
    dialog.geometry("600x600")

    ttk.Label(dialog, text="Sélectionner les modèles:").grid(row=0, column=0, columnspan=2, padx=5, pady=5)
    model_vars = {}
    for i, modele in enumerate(MODELE_MAPPING.keys(), 1):
        var = tk.BooleanVar()
        model_vars[modele] = var
        ttk.Checkbutton(dialog, text=modele, variable=var).grid(row=i, column=0, columnspan=2, padx=5, pady=2, sticky="w")

    ttk.Label(dialog, text="Coloris:").grid(row=len(MODELE_MAPPING) + 1, column=0, padx=5, pady=5)
    coloris_combo = ttk.Combobox(dialog, values=list(COLORIS_MAPPING.keys()), state="readonly")
    coloris_combo.grid(row=len(MODELE_MAPPING) + 1, column=1, padx=5, pady=5)

    ttk.Label(dialog, text="Pointures (ex: 36-42):").grid(row=len(MODELE_MAPPING) + 2, column=0, padx=5, pady=5)
    pointures_entry = ttk.Entry(dialog)
    pointures_entry.grid(row=len(MODELE_MAPPING) + 2, column=1, padx=5, pady=5)

    ttk.Label(dialog, text="Nombre de paires par pointure:").grid(row=len(MODELE_MAPPING) + 3, column=0, padx=5, pady=5)
    nb_paire_entry = ttk.Entry(dialog)
    nb_paire_entry.grid(row=len(MODELE_MAPPING) + 3, column=1, padx=5, pady=5)

    ttk.Label(dialog, text="OF:").grid(row=len(MODELE_MAPPING) + 4, column=0, padx=5, pady=5)
    of_entry = ttk.Entry(dialog)
    of_entry.grid(row=len(MODELE_MAPPING) + 4, column=1, padx=5, pady=5)

    ttk.Label(dialog, text="Date réception:").grid(row=len(MODELE_MAPPING) + 5, column=0, padx=5, pady=5)
    date_entry = ttk.Entry(dialog)
    date_entry.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
    date_entry.grid(row=len(MODELE_MAPPING) + 5, column=1, padx=5, pady=5)

    progress = ttk.Progressbar(dialog, orient="horizontal", length=300, mode="determinate")
    progress.grid(row=len(MODELE_MAPPING) + 6, column=0, columnspan=2, pady=10)

    generated_codes = []

    def lancer_generation():
        nonlocal generated_codes
        generated_codes = []
        try:
            selected_models = [model for model, var in model_vars.items() if var.get()]
            if not selected_models:
                messagebox.showerror("Erreur", "Sélectionnez au moins un modèle.")
                return

            coloris = coloris_combo.get()
            pointures = pointures_entry.get().split("-")
            nb_paire = nb_paire_entry.get()
            of = of_entry.get()
            date = date_entry.get()

            start = int(pointures[0])
            end = int(pointures[1]) if len(pointures) > 1 else start
            total = len(selected_models) * (end - start + 1)
            progress["maximum"] = total
            current = 0

            for modele in selected_models:
                for pointure in range(start, end + 1):
                    result = generer_code_barre(modele, str(pointure), nb_paire, date, of, coloris, display=False)
                    if result:
                        generated_codes.append(result)
                    current += 1
                    progress["value"] = current
                    dialog.update()

            print_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Succès", f"{len(generated_codes)} codes-barres générés! Cliquez sur 'Imprimer' pour l'impression.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {str(e)}")

    def imprimer_codes():
        if not generated_codes:
            messagebox.showerror("Erreur", "Aucun code à imprimer.")
            return

        try:
            printer_name = win32print.GetDefaultPrinter()
            hprinter = win32print.OpenPrinter(printer_name)
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc('Impression Multi-Codes')
            hdc.StartPage()

            x_pos = 100
            y_pos = 100
            codes_per_page = 8

            for i, code_data in enumerate(generated_codes):
                if i > 0 and i % codes_per_page == 0:
                    hdc.EndPage()
                    hdc.StartPage()
                    y_pos = 100

                img = Image.open(code_data['filename']).convert('RGB')
                dib = ImageWin.Dib(img)
                dib.draw(hdc.GetHandleOutput(), (x_pos, y_pos, x_pos + 250, y_pos + 80))

                hdc.TextOut(x_pos, y_pos + 90, f"Mod: {code_data['modele']} Pt: {code_data['pointure']}")
                hdc.TextOut(x_pos, y_pos + 110, f"OF: {code_data['of']} Col: {code_data['coloris']}")

                y_pos += 150

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            win32print.ClosePrinter(hprinter)
            messagebox.showinfo("Succès", "Impression terminée!")
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'impression: {str(e)}")

    print_btn = ttk.Button(dialog, text="Imprimer les Codes", command=imprimer_codes, bootstyle=PRIMARY, state=tk.DISABLED)
    print_btn.grid(row=len(MODELE_MAPPING) + 7, column=0, pady=10)
    ttk.Button(dialog, text="Lancer la Génération", command=lancer_generation, bootstyle=SUCCESS).grid(row=len(MODELE_MAPPING) + 7, column=1, pady=10)

def reset_database():
    if not messagebox.askyesno("Confirmation ⚠️", "Voulez-vous vraiment réinitialiser la base de données ?"):
        return

    try:
        cursor.execute("DELETE FROM etiquettes")
        cursor.execute("DELETE FROM stock")
        cursor.execute("DELETE FROM sorties")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('etiquettes', 'stock', 'sorties')")
        conn.commit()

        for table_widget in [table, table_stock, table_sorties]:
            for item in table_widget.get_children():
                table_widget.delete(item)
        messagebox.showinfo("Succès ✅", "Base de données réinitialisée.")
    except Exception as e:
        messagebox.showerror("Erreur 🚫", f"Erreur lors de la réinitialisation: {e}")

def populate_etiquettes_db():
    pointures = [str(i) for i in range(28, 46)]
    modeles = list(MODELE_MAPPING.keys())
    coloris_list = list(COLORIS_MAPPING.keys())
    nb_paire = "01"
    date_reception = "2025-05-23"
    of = "OF0001"

    try:
        for modele in modeles:
            for pointure in pointures:
                for coloris in coloris_list:
                    modele_code = MODELE_MAPPING[modele]
                    coloris_code = COLORIS_MAPPING[coloris]
                    code = f"25{pointure}{nb_paire}{modele_code}{coloris_code}"
                    cursor.execute('''
                        INSERT OR IGNORE INTO etiquettes (modele, pointure, nb_paire, date_reception, coloris, code, of)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (modele, pointure, nb_paire, date_reception, coloris, code, of))
        conn.commit()
        messagebox.showinfo("Succès ✅", "Données ajoutées à la table etiquettes.")
        for item in table.get_children():
            table.delete(item)
        charger_donnees_db()
    except Exception as e:
        messagebox.showerror("Erreur 🚫", f"Erreur lors de l'ajout des données: {e}")

def validate_code(code):
    if not code or len(code) != 11:
        raise ValueError("Code doit être de 11 chiffres.")
    year = code[0:2]
    pointure = code[2:4]
    nb_paire = code[4:6]
    modele_code = code[6:8]
    coloris_code = code[8:11]

    if year != "25":
        raise ValueError("Code doit commencer par '25'.")
    if not pointure.isdigit() or not (28 <= int(pointure) <= 45):
        raise ValueError("Pointure invalide (28–45).")
    if not nb_paire.isdigit() or not (1 <= int(nb_paire) <= 99):
        raise ValueError("Nombre de paires invalide (1–99).")
    if modele_code not in REVERSE_MODELE_MAPPING:
        raise ValueError(f"Code modèle invalide. Attendu: {list(REVERSE_MODELE_MAPPING.keys())}.")
    if coloris_code not in REVERSE_COLORIS_MAPPING:
        raise ValueError(f"Code coloris invalide. Attendu: {list(REVERSE_COLORIS_MAPPING.keys())}.")
    return year, pointure, nb_paire, modele_code, coloris_code

def ajouter_ligne_table(event=None):
    code = scan_code_var.get().strip()
    try:
        year, pointure, nb_paire, modele_code, coloris_code = validate_code(code)
        modele = REVERSE_MODELE_MAPPING[modele_code]
        coloris = REVERSE_COLORIS_MAPPING[coloris_code]
        date_rec = "2025-05-23"
        of = "OF0001"

        cursor.execute('''
            INSERT OR IGNORE INTO etiquettes (modele, pointure, nb_paire, date_reception, coloris, code, of)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (modele, pointure, nb_paire, date_rec, coloris, code, of))
        conn.commit()

        table.insert("", "end", values=(modele, pointure, nb_paire, date_rec, coloris, code))
        scan_code_var.set("")
    except Exception as e:
        messagebox.showerror("Erreur 🚫", f"Code invalide ou erreur: {e}")

def ajouter_ligne_stock_scan(event=None):
    code = stock_scan_code_var.get().strip()
    try:
        year, pointure, nb_paire, modele_code, coloris_code = validate_code(code)
        designation = REVERSE_MODELE_MAPPING[modele_code]
        coloris = REVERSE_COLORIS_MAPPING[coloris_code]

        dialog = tk.Toplevel(root)
        dialog.title("Ajouter au Stock")
        dialog.geometry("300x200")

        ttk.Label(dialog, text="Lieu de stockage:").pack(pady=5)
        lieu_var = tk.StringVar()
        ttk.Combobox(dialog, textvariable=lieu_var, values=["Imbert-Mnif", "Decathlon"], state="readonly").pack(pady=5)

        ttk.Label(dialog, text="Date réception (AAAA-MM-JJ):").pack(pady=5)
        date_entry = ttk.Entry(dialog)
        date_entry.pack(pady=5)
        date_entry.insert(0, "2025-05-23")

        def submit():
            lieu_stockage = lieu_var.get()
            date_reception = date_entry.get().strip()
            try:
                if not lieu_stockage or lieu_stockage not in ["Imbert-Mnif", "Decathlon"]:
                    raise ValueError("Lieu de stockage invalide.")
                datetime.datetime.strptime(date_reception, "%Y-%m-%d")

                cursor.execute('''
                    INSERT OR IGNORE INTO stock (code, designation, coloris, pointure, nb_paire, date_reception, lieu_stockage)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (code, designation, coloris, pointure, nb_paire, date_reception, lieu_stockage))
                conn.commit()

                table_stock.insert("", "end", values=(
                    code, designation, coloris, pointure, nb_paire, date_reception, lieu_stockage))
                stock_scan_code_var.set("")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Erreur 🚫", f"Erreur: {e}")

        ttk.Button(dialog, text="Valider", command=submit, bootstyle=SUCCESS).pack(pady=10)
        dialog.transient(root)
        dialog.grab_set()
        root.wait_window(dialog)

    except Exception as e:
        messagebox.showerror("Erreur 🚫", f"Code invalide ou erreur: {e}")

def ajouter_ligne_sortie_scan(event=None):
    code = sortie_scan_code_var.get().strip()
    try:
        year, pointure, nb_paire, modele_code, coloris_code = validate_code(code)
        designation = REVERSE_MODELE_MAPPING[modele_code]
        coloris = REVERSE_COLORIS_MAPPING[coloris_code]

        dialog = tk.Toplevel(root)
        dialog.title("Ajouter à la Sortie")
        dialog.geometry("300x200")

        ttk.Label(dialog, text="Nombre de paires:").pack(pady=5)
        nb_paire_entry = ttk.Entry(dialog)
        nb_paire_entry.pack(pady=5)
        nb_paire_entry.insert(0, nb_paire)

        ttk.Label(dialog, text="Date sortie (AAAA-MM-JJ):").pack(pady=5)
        date_entry = ttk.Entry(dialog)
        date_entry.pack(pady=5)
        date_entry.insert(0, "2025-05-23")

        def submit():
            try:
                int_nb_paire = int(nb_paire_entry.get().strip())
                date_sortie = date_entry.get().strip()
                if int_nb_paire < 1:
                    raise ValueError("Nombre de paires doit être positif.")
                datetime.datetime.strptime(date_sortie, "%Y-%m-%d")

                cursor.execute('''
                    SELECT nb_paire FROM stock WHERE code = ? AND lieu_stockage = 'Decathlon'
                ''', (code,))
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Aucun stock trouvé pour ce code à Decathlon.")

                current_stock = int(result[0])
                if current_stock < int_nb_paire:
                    raise ValueError(f"Stock insuffisant à Decathlon: {current_stock} paires disponibles.")

                new_stock = current_stock - int_nb_paire
                if new_stock == 0:
                    cursor.execute('''
                        DELETE FROM stock WHERE code = ? AND lieu_stockage = 'Decathlon'
                    ''', (code,))
                else:
                    cursor.execute('''
                        UPDATE stock SET nb_paire = ? WHERE code = ? AND lieu_stockage = 'Decathlon'
                    ''', (str(new_stock), code))

                cursor.execute('''
                    INSERT OR IGNORE INTO sorties (code, designation, coloris, pointure, nb_paire, date_sortie)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (code, designation, coloris, pointure, str(int_nb_paire), date_sortie))
                conn.commit()

                table_sorties.insert("", "end",
                                     values=(code, designation, coloris, pointure, str(int_nb_paire), date_sortie))
                sortie_scan_code_var.set("")
                dialog.destroy()

                for item in table_stock.get_children():
                    table_stock.delete(item)
                cursor.execute("SELECT code, designation, coloris, pointure, nb_paire, date_reception, lieu_stockage FROM stock")
                for row in cursor.fetchall():
                    table_stock.insert("", "end", values=row)

            except Exception as e:
                messagebox.showerror("Erreur 🚫", f"Erreur: {e}")

        ttk.Button(dialog, text="Valider", command=submit, bootstyle=SUCCESS).pack(pady=10)
        dialog.transient(root)
        dialog.grab_set()
        root.wait_window(dialog)

    except Exception as e:
        messagebox.showerror("Erreur 🚫", f"Code invalide ou erreur: {e}")

def charger_donnees_db():
    for table_widget in [table, table_stock, table_sorties]:
        for item in table_widget.get_children():
            table_widget.delete(item)

    cursor.execute("SELECT modele, pointure, nb_paire, date_reception, coloris, code FROM etiquettes")
    for row in cursor.fetchall():
        table.insert("", "end", values=row)

    cursor.execute("SELECT code, designation, coloris, pointure, nb_paire, date_reception, lieu_stockage FROM stock")
    for row in cursor.fetchall():
        table_stock.insert("", "end", values=row)

    cursor.execute("SELECT code, designation, coloris, pointure, nb_paire, date_sortie FROM sorties")
    for row in cursor.fetchall():
        table_sorties.insert("", "end", values=row)

# --- INTERFACE ---
root = ttk.Window(themename="flatly")
root.title("Étiquettes & Gestion de Stock 🏷️")
root.geometry("1200x800")

notebook = ttk.Notebook(root, bootstyle=PRIMARY)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Generation Frame
frame_gen = ttk.Frame(notebook)
notebook.add(frame_gen, text="Générer Étiquette 📄")

labels = ["Modèle 🖌️", "Pointure 👟", "Nombre de paires 📦", "Date réception (AAAA-MM-JJ) 📅",
          "Ordre de fabrication (OF) 🔧", "Coloris 🎨"]
entries = []
for i, label in enumerate(labels):
    ttk.Label(frame_gen, text=label, font=("Arial", 10)).grid(row=i, column=0, sticky="w", padx=10, pady=8)
    if label == "Coloris 🎨":
        entry = ttk.Combobox(frame_gen, values=list(COLORIS_MAPPING.keys()), bootstyle=INFO, state="readonly")
    elif label == "Modèle 🖌️":
        entry = ttk.Combobox(frame_gen, values=list(MODELE_MAPPING.keys()), bootstyle=INFO, state="readonly")
    else:
        entry = ttk.Entry(frame_gen, bootstyle=INFO)
    entry.grid(row=i, column=1, padx=10, pady=8)
    entries.append(entry)

entry_modele, entry_pointure, entry_nb_paire, entry_date, entry_of, entry_coloris = entries

ttk.Button(frame_gen, text="Générer Code-Barres 🏷️", command=lambda: generer_code_barre(
    entry_modele.get(), entry_pointure.get(), entry_nb_paire.get(), entry_date.get(), entry_of.get(), entry_coloris.get())).grid(row=6, column=0, pady=15)
ttk.Button(frame_gen, text="Imprimer Code-Barres 🖨️", command=imprimer_code_barre, bootstyle=PRIMARY).grid(row=6, column=1, pady=15)
ttk.Button(frame_gen, text="Sauvegarder en PDF 📁", command=generer_pdf, bootstyle=INFO).grid(row=6, column=2, pady=15)

code_var = tk.StringVar()
ttk.Label(frame_gen, text="Code généré 🔢:").grid(row=7, column=0, sticky="e")
ttk.Entry(frame_gen, textvariable=code_var, state="readonly", width=40, bootstyle=SECONDARY).grid(row=7, column=1, padx=10, pady=5)

label_img_code = ttk.Label(frame_gen)
label_img_code.grid(row=8, column=0, columnspan=4, pady=20)

# Mass Generation Frame
frame_multi = ttk.Frame(notebook)
notebook.add(frame_multi, text="Génération Multiple 📦")
ttk.Button(frame_multi, text="Ouvrir Génération Multiple", command=generer_multi_codes, bootstyle=SUCCESS).pack(pady=20)

# Scan Frame
frame_scan = ttk.Frame(notebook)
notebook.add(frame_scan, text="Scan & Lecture 📷")

ttk.Label(frame_scan, text="Scanner le code 🔍:", font=("Arial", 10)).grid(row=0, column=0, padx=10, pady=12, sticky="e")
scan_code_var = tk.StringVar()
scan_entry = ttk.Entry(frame_scan, textvariable=scan_code_var, width=50, bootstyle=INFO)
scan_entry.grid(row=0, column=1, padx=10, pady=12)
scan_entry.bind("<Return>", ajouter_ligne_table)

ttk.Button(frame_scan, text="Ajouter ➕", command=ajouter_ligne_table, bootstyle=SUCCESS).grid(row=1, column=0, pady=10)
ttk.Button(frame_scan, text="Réinitialiser Base 🗑️", command=reset_database, bootstyle=DANGER).grid(row=1, column=1, pady=10)

columns = ("Modèle", "Pointure", "Nb Paires", "Date Réception", "Coloris", "Code Complet")
table = ttk.Treeview(frame_scan, columns=columns, show="headings", height=12, bootstyle=PRIMARY)
for col in columns:
    table.heading(col, text=col)
    table.column(col, width=120, anchor="center")
table.grid(row=2, column=0, columnspan=2, padx=15, pady=15, sticky="nsew")

scrollbar = ttk.Scrollbar(frame_scan, orient="vertical", command=table.yview, bootstyle=PRIMARY)
table.configure(yscroll=scrollbar.set)
scrollbar.grid(row=2, column=2, sticky="ns", pady=15)

# Stock Frame
frame_stock = ttk.Frame(notebook)
notebook.add(frame_stock, text="Stock 📦")

stock_frame = ttk.Frame(frame_stock)
stock_frame.pack(fill="x", padx=10, pady=10)

ttk.Label(stock_frame, text="Scanner pour ajouter au stock 🔍:").pack(pady=5)
stock_scan_code_var = tk.StringVar()
stock_scan_entry = ttk.Entry(stock_frame, textvariable=stock_scan_code_var, width=50, bootstyle=INFO)
stock_scan_entry.pack(pady=5)
stock_scan_entry.bind("<Return>", ajouter_ligne_stock_scan)

columns_stock = ("Code", "Désignation", "Coloris", "Pointure", "Nb Paires", "Date Réception", "Lieu Stockage")
table_stock = ttk.Treeview(frame_stock, columns=columns_stock, show="headings", height=12, bootstyle=PRIMARY)
for col in columns_stock:
    table_stock.heading(col, text=col)
    table_stock.column(col, width=120, anchor="center")
table_stock.pack(padx=10, pady=10, fill="both", expand=True)

scrollbar_stock = ttk.Scrollbar(frame_stock, orient="vertical", command=table_stock.yview, bootstyle=PRIMARY)
table_stock.configure(yscroll=scrollbar_stock.set)
scrollbar_stock.pack(side="right", fill="y", padx=(0, 10))

# Sorties Frame
frame_sorties = ttk.Frame(notebook)
notebook.add(frame_sorties, text="Sorties 🚚")

sortie_frame = ttk.Frame(frame_sorties)
sortie_frame.pack(fill="x", padx=10, pady=10)

ttk.Label(sortie_frame, text="Scanner pour ajouter à la sortie 🔍:").pack(pady=5)
sortie_scan_code_var = tk.StringVar()
sortie_scan_entry = ttk.Entry(sortie_frame, textvariable=sortie_scan_code_var, width=50, bootstyle=INFO)
sortie_scan_entry.pack(pady=5)
sortie_scan_entry.bind("<Return>", ajouter_ligne_sortie_scan)

columns_sorties = ("Code", "Désignation", "Coloris", "Pointure", "Nb Paires", "Date Sortie")
table_sorties = ttk.Treeview(frame_sorties, columns=columns_sorties, show="headings", height=12, bootstyle=PRIMARY)
for col in columns_sorties:
    table_sorties.heading(col, text=col)
    table_sorties.column(col, width=120, anchor="center")
table_sorties.pack(padx=10, pady=10, fill="both", expand=True)

scrollbar_sorties = ttk.Scrollbar(frame_sorties, orient="vertical", command=table_sorties.yview, bootstyle=PRIMARY)
table_sorties.configure(yscroll=scrollbar_sorties.set)
scrollbar_sorties.pack(side="right", fill="y", padx=(0, 10))

charger_donnees_db()

root.mainloop()
conn.close()