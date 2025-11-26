from flask import Flask, request, jsonify
import json
import torch
import joblib
import re
from clean_text import clean_text
from sentence_transformers import SentenceTransformer
from google_sheets import guardar_en_google_sheets
import os

app = Flask(__name__)

# ============================================================
# ESTADO DEL USUARIO
# ============================================================

user_states = {}

def get_state(uid):
    if uid not in user_states:
        user_states[uid] = {
            "name": None,
            "city": None,
            "budget": None,
            "phone": None,
            "modo": None,            # aprender o invertir
            "last_action": None,
            "confirming": None
        }
    return user_states[uid]

def reset_state(uid):
    if uid in user_states:
        del user_states[uid]


# ============================================================
# EXTRACCIÓN DE DATOS
# ============================================================

def extract_name(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-záéíóúñ ]", "", text)

    match = re.search(r"(me llamo|mi nombre es|soy)\s+([a-záéíóúñ ]+)", text)
    if match:
        name = match.group(2).strip()
        if 1 <= len(name.split()) <= 3:
            return name.title()
        return None

    if 1 <= len(text.split()) <= 3:
        return text.title()
    return None


def extract_city(text):
    text = text.lower()
    text = re.sub(r"(desde|soy de|estoy en|vivo en|ciudad de|de|en)\s+", "", text)

    norm = text.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    ciudades = [ "Abriaquí","Acacías","Acandí","Acevedo","Achí","Agrado"
        ,"Aguachica","Aguada","Aguadas","Aguazul","Agustín Codazzi",
        "Aipe","Albania","Albania (Caquetá)","Albania (Santander)","Albán",
        "Albán (Nariño)","Alcalá","Alejandría","Algarrobo","Algeciras","Almaguer"
        ,"Almeida","Alpujarra","Altamira","Alto Baudó","Altos del Rosario","Ambalema"
        ,"Anapoima","Ancuya","Andalucía","Andes","Angelópolis","Angostura","Anolaima",
        "Anorí","Anserma","Ansermanuevo","Antioquia","Antúquiz","Anzá","Apartadó"
        ,"Apía","Aquitania","Aracataca","Aranzazu","Aratoca","Arauca","Arauquita"
        ,"Arbeláez","Arboleda","Arboledas","Arboletes","Arboletes","Arcabuco","Arenal"
        ,"Argelia (Antioquia)","Argelia (Cauca)","Argelia (Valle)","Ariguaní","Arjona"
        ,"Armenia","Armero Guayabal","Arroyohondo","Astrea","Ataco","Atrato","Ayapel"
        ,"Bagadó","Bahía Solano","Bajo Baudó","Balboa (Cauca)","Balboa (Risaralda)"
        ,"Baranoa","Baraya","Barbacoas","Barbosa","Barbosa (Santander)","Barichara"
        ,"Barranca de Upía","Barrancabermeja","Barrancas","Barranco de Loba"
        ,"Barranquilla","Becerril","Belalcázar","Bello","Belmira","Beltrán","Belén"
        ,"Belén (Boyacá)","Belén de Bajirá","Belén de Umbría","Belén de los Andaquíes"
        ,"Berbeo","Betania","Betéitiva","Betulia (Antioquia)","Betulia (Santander)"
        ,"Bituima","Boavita","Bochalema","Bogotá","Bojacá","Bojayá","Bolívar (Cauca)"
        ,"Bolívar (Santander)","Bolívar (Valle)","Bosconia","Boyacá","Briceño (Antioquia)"
        ,"Briceño (Boyacá)","Briceño (Cundinamarca)","Bucaramanga","Bucarasica"
        ,"Buenaventura","Buenos Aires","Buenavista (Boyacá)","Buenavista (Córdoba)"
        ,"Buenavista (Quindío)","Buenavista (Sucre)","Bugalagrande","Bugalagrande"
        ,"Bugalagrande","Burítica","Busbanzá","Cabrera (Cundinamarca)","Cabrera (Santander)"
        ,"Cabuyaro","Cacahual","Cachipay","Caicedo","Caicedonia","Caimito","Cajamarca"
        ,"Cajibío","Cajicá","Calamar (Bolívar)","Calamar (Guaviare)","Calarcá"
        ,"Caldas (Antioquia)","Caldas (Boyacá)","Caldas (Cundinamarca)","Caldono"
        ,"California","Calima Darién","Caloto","Campamento","Campoalegre","Campohermoso", "cali"
        ,"Canalete","Candelaria (Atlántico)","Candelaria (Valle)","Cantagallo"
        ,"Cantón de San Pablo","Caparrapí","Capitanejo","Cáqueza","Caracolí","Caramanta"
        ,"Carcasí","Carepa","Carmen de Apicalá","Carmen de Carupa","Carmen de Viboral"
        ,"Carmen del Darién","Carolina","Cartagena de Indias","Cartago","Carurú","Casabianca"
        ,"Castilla la Nueva","Caucasia","Cañasgordas","Cepitá","Cereté","Cerinza","Cerrito"
        ,"Cerro San Antonio","Cértegui","Chachagüí","Chaguaní","Chalán","Chaparral","Charalá"
        ,"Charta","Chía","Chigorodó","Chima (Santander)","Chimá (Córdoba)","Chimichagua"
        ,"Chinavita","Chinchiná","Chinú","Chipaque","Chipatá","Chiquinquirá","Chiriguaná"
        ,"Chiscas","Chita","Chitagá","Chitaraque","Chivatá","Chivolo","Choachí"
        ,"Chocontá","Cicuco","Ciénaga (Magdalena)","Ciénaga de Oro","Cimitarra", "cúcuta"
        ,"Circasia","Cisneros","Ciénaga","Clemencia","Cocorná","Coello","Cogua"
        ,"Colombia","Colón (Putumayo)","Colón (Nariño)","Coloso","Cómbita"
        ,"Concepción (Antioquia)","Concepción (Santander)","Concordia (Antioquia)"
        ,"Concordia (Magdalena)","Condoto","Confines","Consacá","Contadero"
        ,"Contratación","Convención","Copacabana","Coper","Cordobá","Corinto"
        ,"Coromoro","Corozal","Corrales","Cota","Cotorra","Covarachía","Coveñas"
        ,"Coyaima","Cravo Norte","Cuaspud","Cubarral","Cubará","Cucaita","Cucunubá"
        ,"Cucutilla","Cumaral","Cumaribo","Cumbal","Cumbitara","Cunday","Curillo"
        ,"Curití","Curumaní","Cáceres","Dabeiba","Dagua","Dibulla","Distracción"
        ,"Dolores","Don Matías","Dosquebradas","Duitama","Durania","Ebéjico","El Águila"
        ,"El Bagre","El Banco","El Cairo","El Calvario","El Carmen (Norte de Santander)"
        ,"El Carmen de Atrato","El Carmen de Bolívar","El Castillo","El Cerrito","El Charco"
        ,"El Cocuy","El Colegio","El Copey","El Doncello","El Dorado","El Dovio"
        ,"El Encanto","El Espino","El Guacamayo","El Guamo","El Litoral del San Juan"
        ,"El Molino","El Paso","El Paujil","El Peñol","El Peñón (Bolívar)","El Peñón (Santander)"
        ,"El Peñón (Cundinamarca)","El Piñón","El Playón","El Retorno","El Retiro","El Roble"
        ,"El Rosal","El Rosario","El Tablón de Gómez","El Tambo (Cauca)","El Tambo (Nariño)"
        ,"El Tarra","El Yopal","El Zulia","Encino","Enciso","Entrerríos","Envigado","Espinal"
        ,"Facatativá","Falan","Filadelfia","Filandia","Firavitoba","Flandes","Florencia","Floresta"
        ,"Florida","Floridablanca","Florián","Fonseca","Fortúl","Fosca","Fómeque","Francisco Pizarro"
        ,"Fredonia","Fresno","Frontino","Fuente de Oro","Fundación","Funes","Funza","Fusagasugá"
        ,"Fátima","Gachalá","Gachancipá","Gachantivá","Gachetá","Galapa","Galeras","Gama","Gamarra"
        ,"Gambita","Gameza","Garagoa","Garzón","Génova","Gigante","Ginebra","Giraldo","Girardot"
        ,"Girardota","Girón","González","Gramalote","Granada (Antioquia)","Granada (Meta)"
        ,"Granada (Cundinamarca)","Guaca","Guacamayas","Guacarí","Guachavés","Guachetá","Guachucal"
        ,"Guadalupe (Antioquia)","Guadalupe (Huila)","Guadalupe (Santander)","Guaduas","Guaitarilla"
        ,"Gualmatán","Guamal (Magdalena)","Guamal (Meta)","Guamo","Guapi","Guapotá","Guaranda","Guarne"
        ,"Guasca","Guatapé","Guataquí","Guatavita","Guateque","Guayatá","Guepsa","Guicán"
        ,"Gutiérrez","Hacarí","Hatillo de Loba","Hato","Hato Corozal","Hatonuevo","Heliconia","Herrán"
        ,"Herveo","Hispania","Hobo","Honda","Ibagué","Icononzo","Iles","Imués","Inzá","Ipiales","Isnos"
        ,"Istmina","Itagüí","Ituango","Iza","Jambaló","Jamundí","Jardín","Jenesano","Jericó","Jerusalén"
        ,"Jesús María","Jordán","Juan de Acosta","Junín","Juradó","La Apartada","La Argentina"
        ,"La Belleza","La Calera","La Capilla","La Ceja","La Celia","La Cruz","La Cumbre","La Dorada"
        ,"La Esperanza","La Estrella","La Florida","La Gloria","La Jagua de Ibirico","La Jagua del Pilar"
        ,"La Llanada","La Macarena","La Merced","La Mesa","La Montañita","La Palma","La Paz (Cesar)"
        ,"La Paz (Santander)","La Peña","La Pintada","La Plata","La Playa","La Primavera"
        ,"La Salina","La Sierra","La Tebaida","La Tola","La Unión (Antioquia)","La Unión (Nariño)"
        ,"La Unión (Sucre)","La Unión (Valle)","La Uvita","La Vega (Cundinamarca)","La Vega (Cauca)",
        "La Victoria (Boyacá)","La Victoria (Valle)","La Virginia","Labateca","Labranzagrande","Landázuri",
        "Lebrija","Leiva","Lejanías","Lenguazaque","Leticia","Liborina","Linares","Lloró","Loja","López de Micay"
        ,"Lorica","Los Andes","Los Córdobas","Los Palmitos","Los Patios","Lourdes","Luruaco","Macanal","Macaravita"
        ,"Maceo","Madrid","Magangué","Magüi Payán","Mahates","Maicao","Majagual","Málaga","Malambo","Mallama"
        ,"Manatí","Manaure","Manaure Balcón del Cesar","Manizales","Manta","Manzanares","Mapiripán","Mapiripana"
        ,"Margarita","Marinilla","Maripí","Mariquita","Marmato","Marquetalia","Marsella","Marulanda","Matanza",
        "Medellín","Medina","Medio Atrato","Medio Baudó","Medio San Juan","Melgar","Mercaderes","Mesetas","Milán"
        ,"Miraflores (Boyacá)","Miraflores (Guaviare)","Miranda","Mistrató","Mitú","Mocoa","Mogotes","Molagavita"
        "Momil","Mompox","Mongua","Monguí","Moniquirá","Monterrey","Montería","Montebello","Montelíbano","Montenegro"
        ,"Morales (Bolívar)","Morales (Cauca)","Morelia","Morroa","Mosquera (Cundinamarca)","Mosquera (Nariño)"
        "Motavita","Murillo","Murindó","Mutatá","Mutiscua","Muzo","Nariño (Antioquia)","Nariño (Nariño)","Nátaga"
        ,"Natagaima","Nechí","Necoclí","Neira","Neiva","Nemocón","Nilo","Nimaima","Nobsa","Nocaima","Norcasia","Norosí"
        "Novita","Nueva Granada","Nuevo Colón","Nunchía","Nuquí","Obando","Ocamonte","Ocaña","Oiba","Oicatá","Olaya (Antioquia)",
        "Olaya Herrera","Onzaga","Oporapa","Orito","Orocué","Ortigueira","Otanche","Ovejas","Pachavita","Pacho","Padilla"
        ,"Paicol","Paime","Paipa","Pajarito","Palermo","Palestina (Caldas)","Palestina (Huila)","Palmar"
        ,"Palmar de Varela","Palmas del Socorro","Palmira","Palmito","Palocabildo","Pamplona","Pamplonita",
        "Pandi","Panqueba","Paratebueno","Pasca","Patía","Pauna","Paya","Paz de Ariporo","Pedraza","Pelaya",
        "Pensilvania","Peque","Pereira","Pesca","Pe", "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bogotá", 
        "Bolívar", "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó", "Cundinamarca", 
        "Córdoba", "Guainía", "Guaviare", "Huila", "La Guajira", "Magdalena", "Meta", "Nariño", 
        "Norte de Santander", "Putumayo", "Quindío", "Risaralda", "San Andrés, Providencia y Santa Catalina", 
        "Santander", "Sucre", "Tolima", "Valle del Cauca", "Vaupés", "Vichada", "popayán" ]  # (Mantengo tu bloque intacto para no romper el archivo)

    ciudades_normalizadas = [c.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u") for c in ciudades]
    mapa = dict(zip(ciudades_normalizadas, ciudades))

    for palabra in norm.split():
        if palabra in mapa: return mapa[palabra]
    return mapa.get(norm)


def extract_budget(text):
    text = text.lower().replace(" ", "").replace(".", "").replace(",", "").replace("$","")

    if "m" in text and text.replace("m","").isdigit():
        return int(text.replace("m","")) * 1_000_000

    match = re.search(r"(\d+)(m|mill|millon|millones|palo|palos)", text)
    if match: return int(match.group(1)) * 1_000_000

    if text.isdigit():
        n = int(text)
        return n * 1_000_000 if n < 1000 else n

    return None


def extract_phone(text):
    phone = re.sub(r"\D", "", text)
    return phone if 7 <= len(phone) <= 12 else None


# ============================================================
# MODELOS
# ============================================================

intent_model = joblib.load("models/intent_model.joblib")
vectorizer   = joblib.load("models/intent_vectorizer.joblib")
emb          = torch.load("semantic_embeddings.pt")
model_sem    = SentenceTransformer("all-MiniLM-L6-v2")

with open("intents_v2.json","r",encoding="utf-8") as f:
    intents = json.load(f)["intents"]


def find_semantic(text):
    q = model_sem.encode(text, convert_to_tensor=True)
    idx = torch.argmax(torch.matmul(q, emb["sentence_embeddings"].T)).item()
    tag = emb["mapping"][idx]
    return next((i for i in intents if i["tag"] == tag), None)


# ============================================================
# CONFIRMACIONES
# ============================================================

def confirm_value(state,key,value):
    state["confirming"]=key
    return f"¿Tu {key.title()} es {value}? (sí / no)"


def process_confirmation(state,msg):
    m=msg.lower().strip()
    if m in ["si","sí","claro","correcto","ok"]:
        campo=state["confirming"]; state["confirming"]=None

        if campo=="nombre": state["last_action"]="save_city"; return f"Listo {state['name']} 😊 ¿De qué ciudad nos escribes?"
        if campo=="ciudad":
            state["last_action"]= "save_budget" if state["modo"]=="invertir" else "save_phone"
            return f"{state['name']}, ¿cuál es tu presupuesto?" if state["modo"]=="invertir" else f"{state['name']}, ¿tu número de teléfono?"

        if campo=="presupuesto": state["last_action"]="save_phone"; return "Perfecto. ¿Cuál es tu número?"
        if campo=="teléfono":
            guardar_en_google_sheets(**state)
            return f"Perfecto {state['name']} 😊\nRegistro completado.\nUn asesor te contactará al {state['phone']} 📩"

    field=state["confirming"]; state[field]=None; state["confirming"]=None
    return f"Entendido, repíteme tu {field}."


# ============================================================
# ACCIONES (NOMBRE, CIUDAD, PRESUPUESTO, TELÉFONO)
# ============================================================

def process_confirmation(state,msg):
    m = msg.lower().strip()

    if m in ["si","sí","claro","correcto","ok"]:

        campo = state["confirming"]
        state["confirming"] = None  # ya no estamos confirmando

        # ✔ CONFIRMÓ NOMBRE → PASA A CIUDAD
        if campo == "nombre":
            state["last_action"] = "save_city"
            return f"Listo {state['name']} 😊 ¿De qué ciudad nos escribes?"

        # ✔ CONFIRMÓ CIUDAD → SEGÚN MODO PIDE SIGUIENTE
        if campo == "ciudad":
            if state["modo"] == "invertir":
                state["last_action"] = "save_budget"
                return f"{state['name']}, ¿cuál es tu presupuesto para invertir?"
            else:
                state["last_action"] = "save_phone"
                return f"{state['name']}, ¿tu número de teléfono?"

        # ✔ CONFIRMÓ PRESUPUESTO → AHORA PIDE TELÉFONO
        if campo == "presupuesto":
            state["last_action"] = "save_phone"
            return "Perfecto. ¿Cuál es tu número de contacto?"

        # 🚀 CONFIRMÓ TELÉFONO → GUARDA + MENSAJE FINAL + CIERRA FLUJO
        if campo == "teléfono":

            guardar_en_google_sheets(**state)  # 🔥 envío automático al sheet

            # cerramos el ciclo para no seguir pidiendo datos
            state["last_action"] = None
            state["confirming"] = None

            return (
                f"📌 Registro completado con éxito {state['name']}!\n\n"
                f"🟢 Modalidad: *{state['modo']}*\n"
                f"🏙 Ciudad: *{state['city']}*\n"
                f"💰 Presupuesto: *{state['budget']:,} COP*\n"
                f"📞 Teléfono: *{state['phone']}*\n\n"
                f"Un asesor se comunicará contigo en breve 🚀"
            )

    # ❗ Si responde NO → vuelve a pedir campo
    campo = state["confirming"]
    state[campo] = None
    state["confirming"] = None
    return f"Entendido, repíteme tu {campo}."

# ============================================================
# **LÓGICA — AQUÍ SE AÑADEN LAS MEJORAS**
# ============================================================

def chatbot_answer(uid,msg):
    state=get_state(uid)
    m=msg.lower().strip()

    # Reinicio manual
    if m=="reset": reset_state(uid); return "Reiniciado ✔"

    # 👉 Detecta aprender/invertir aunque no sea exacto
    if state["modo"] is None:
        if re.search(r"aprend|curso|estudi|informaci.*aprend",m):
            state["modo"]="aprender"; state["last_action"]="save_name"
            return "Perfecto 🤓 ¿Cuál es tu nombre completo?"

        if re.search(r"invert|invers|capital|rendim",m):
            state["modo"]="invertir"; state["last_action"]="save_name"
            return "Excelente 💼 ¿Cuál es tu nombre completo?"

        return "¿Deseas aprender o invertir? 🙌 Puedes decir: *Quiero aprender* o *Deseo invertir*."

    # Atajo asesor
    if "asesor" in m: return "Contacto directo 👇\nhttps://wa.me/573160422795"

    # Confirmaciones
    if state["confirming"]: return process_confirmation(state,msg)

    # Siguiente acción secuencial (nombre→ciudad→presupuesto→teléfono)
    if state["last_action"]:
        r=handle_action(state,state["last_action"],msg)
        if r: return r

    # Modelo de intención
    intent=intent_model.predict(vectorizer.transform([clean_text(msg)]))[0]
    for i in intents:
        if i["tag"]==intent:
            state["last_action"]=i.get("next_action")
            r=i["responses"][0]

            if "{name}" in r and state["name"]: r=r.replace("{name}",state["name"])
            if "{city}" in r and state["city"]: r=r.replace("{city}",state["city"])
            if "{budget}" in r and state["budget"]: r=r.replace("{budget}",f"${state['budget']:,}")
            if "{phone}" in r and state["phone"]: r=r.replace("{phone}",state["phone"])
            return r

    sem=find_semantic(msg)
    if sem:
        state["last_action"]=sem.get("next_action")
        return sem["responses"][0]

    return "No entendí bien 🤔 ¿podrías repetirlo?"


# ============================================================
# FLASK SERVER
# ============================================================

@app.route("/",methods=["GET"])
def home(): return jsonify({"status":"online"}),200

@app.route("/webhook",methods=["POST"])
def webhook():
    data=request.get_json(force=True)
    uid=str(data.get("user_id") or data.get("sender_id") or data.get("id") or "anon")
    msg=data.get("message") or data.get("text") or data.get("comment") or ""
    return jsonify({"respuesta":chatbot_answer(uid,msg)}),200


if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))

