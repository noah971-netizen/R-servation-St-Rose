import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Réservation St-Rose", layout="wide")

# --- CONNEXION ---
@st.cache_resource
def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)
    return client.open_by_key("1DivlVVVMka80mXPp6NRuUzDrzgUtXS5Ps-U-pVhKDHI").sheet1

sheet = get_sheet()

# --- SÉCURITÉ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    if st.text_input("Code d'accès", type="password") == "1234":
        st.session_state.logged_in = True
        st.rerun()
    st.stop()

# --- FONCTION DISPONIBILITÉ ---
def est_disponible(v, d_dep_req, d_ret_req, ligne_exclusion=None):
    f_panne = f"panne_{v}.txt"
    if os.path.exists(f_panne) and open(f_panne, "r").read().strip() == "En panne":
        return False, "Ce véhicule est en panne."
    
    data = sheet.get_all_values()
    if len(data) > 1:
        for i, row in enumerate(data[1:]):
            if i + 2 == ligne_exclusion: continue
            if len(row) > 6 and row[1] == v:
                try:
                    d_dep_exist = datetime.strptime(row[2], "%d/%m/%Y").date()
                    d_ret_exist = datetime.strptime(row[4], "%d/%m/%Y").date()
                    if d_dep_req <= d_ret_exist and d_ret_req >= d_dep_exist:
                        return False, "Créneau déjà pris par une autre réservation."
                except: continue
    return True, ""

# --- INTERFACE ---
t1, t2, t3, t4 = st.tabs(["📅 Planning", "➕ Réserver", "✏️ Modification", "🔧 Pannes"])

with t1:
    data = sheet.get_all_values()
    if len(data) > 1:
        df = pd.DataFrame(data[1:], columns=data[0])
        st.dataframe(df.drop(df.columns[6], axis=1), use_container_width=True)
    else: st.info("Aucune réservation trouvée.")

with t2:
    v = st.selectbox("Véhicule", ["Doblo", "Dyna"])
    with st.form("ajout"):
        nom = st.text_input("Prénom")
        col1, col2 = st.columns(2)
        d_dep = col1.date_input("Date Départ")
        h_dep = col2.time_input("Heure Départ")
        d_ret = col1.date_input("Date Retour")
        h_ret = col2.time_input("Heure Retour")
        code = st.text_input("Code Secret", type="password")
        if st.form_submit_button("Valider"):
            if not nom or not code:
                st.warning("⚠️ Merci de remplir tous les champs (Prénom et Code) !")
            else:
                dispo, msg = est_disponible(v, d_dep, d_ret)
                if not dispo: st.error(f"❌ {msg}")
                else:
                    sheet.append_row([nom, v, d_dep.strftime("%d/%m/%Y"), str(h_dep), d_ret.strftime("%d/%m/%Y"), str(h_ret), code])
                    st.success("✅ Votre réservation a bien été prise avec succès !")
                    st.balloons()
                    st.rerun()

with t3:
    st.subheader("✏️ Modification ou Suppression")
    if "code_modif" not in st.session_state: st.session_state.code_modif = ""
    code_acces = st.text_input("Entrez votre code secret", value=st.session_state.code_modif, type="password")
    st.session_state.code_modif = code_acces
    
    if code_acces:
        data = sheet.get_all_values()
        for i, row in enumerate(data[1:]):
            if row[6] == code_acces:
                with st.form("modif_form"):
                    n_nom = st.text_input("Prénom", value=row[0])
                    n_v = st.selectbox("Véhicule", ["Doblo", "Dyna"], index=["Doblo", "Dyna"].index(row[1]))
                    n_d_dep = st.date_input("Date Départ", value=datetime.strptime(row[2], "%d/%m/%Y").date())
                    n_d_ret = st.date_input("Date Retour", value=datetime.strptime(row[4], "%d/%m/%Y").date())
                    if st.form_submit_button("Sauvegarder"):
                        if not n_nom: st.warning("⚠️ Le prénom est obligatoire.")
                        else:
                            dispo, msg = est_disponible(n_v, n_d_dep, n_d_ret, ligne_exclusion=i+2)
                            if not dispo: st.error(f"❌ {msg}")
                            else:
                                sheet.update(range_name=f"A{i+2}:G{i+2}", values=[[n_nom, n_v, n_d_dep.strftime("%d/%m/%Y"), row[3], n_d_ret.strftime("%d/%m/%Y"), row[5], code_acces]])
                                st.success("✅ Modification enregistrée avec succès !")
                                st.balloons()
                                st.rerun()
                if st.button("❌ Supprimer cette réservation"):
                    sheet.delete_rows(i+2)
                    st.warning("🗑️ Réservation supprimée.")
                    st.rerun()

with t4:
    st.subheader("État des véhicules")
    cols = st.columns(2)
    for i, v in enumerate(["Doblo", "Dyna"]):
        f = f"panne_{v}.txt"
        etat = "En panne" if (os.path.exists(f) and open(f, "r").read().strip() == "En panne") else "OK"
        with cols[i]:
            if etat == "En panne": st.error(f"### 🚨 {v} : EN PANNE")
            else: st.success(f"### ✅ {v} : EN SERVICE")
            if st.button(f"Basculer état de {v}", key=v):
                new_etat = "En panne" if etat == "OK" else "OK"
                open(f, "w").write(new_etat)
                st.rerun()