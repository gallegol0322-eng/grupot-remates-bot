from flask import Flask, request, jsonify
import json
import torch
import joblib
import re
from clean_text import clean_text
from sentence_transformers import SentenceTransformer
from google_sheets import guardar_en_google_sheets  # si no usarás Sheets, comenta esta línea



def limpiar_trigger(text):
    # elimina SOLO si prueba está al inicio, así no afecta el chat normal
    return re.sub(r"^prueba\s*", "", text.strip(), flags=re.IGNORECASE)




app = Flask(__name__)

# ==============================================
#    CONTROL DE ESTADO POR USUARIO (CORRECTO)
# ==============================================
user_states = {}

def get_state(uid):
    if uid not in user_states:
        user_states[uid] = {
            "name": None,
            "city": None,
            "budget": None,
            "phone": None,
            "modo": None,
            "last_action": None,
            "confirming": None
        }
    return user_states[uid]


# ==============================================
#  📌  EXTRACCIÓN DE DATOS DEL USUARIO
# ==============================================
def extract_name(text):
    text = limpiar_trigger(text)
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Záéíóúñ ]", "", text)

    match = re.search(r"(me llamo|mi nombre es|soy)\s+([a-zA-Záéíóúñ ]+)", text)
    if match:
        name = match.group(2).strip()
        if 1 <= len(name.split()) <= 3: return name.title()

    if 1 <= len(text.split()) <= 3:
        return text.title()

    return None


def extract_city(text):
    text = limpiar_trigger(text)
    text = text.lower().strip()
    text = re.sub(r"(desde|soy de|estoy en|vivo en|ciudad de|de|en)\s+", "", text)
    norm = (text.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u"))

    ciudades = ["Abriaquí","Acacías","Acandí","Acevedo","Achí","Agrado",
        "Aguachica","Aguada","Aguadas","Aguazul","Agustín Codazzi",
        "Aipe","Albania","Albania (Caquetá)","Albania (Santander)","Albán",
        "Albán (Nariño)","Alcalá","Alejandría","Algarrobo","Algeciras","Almaguer",
        "Almeida","Alpujarra","Altamira","Alto Baudó","Altos del Rosario","Ambalema",
        "Anapoima","Ancuya","Andalucía","Andes","Angelópolis","Angostura","Anolaima",
        "Anorí","Anserma","Ansermanuevo","Antioquia","Antúquiz","Anzá","Apartadó",
        "Apía","Aquitania","Aracataca","Aranzazu","Aratoca","Arauca","Arauquita",
        "Arbeláez","Arboleda","Arboledas","Arboletes","Arcabuco","Arenal",
        "Argelia (Antioquia)","Argelia (Cauca)","Argelia (Valle)","Ariguaní","Arjona",
        "Armenia","Armero Guayabal","Arroyohondo","Astrea","Ataco","Atrato","Ayapel",
        "Bagadó","Bahía Solano","Bajo Baudó","Balboa (Cauca)","Balboa (Risaralda)",
        "Baranoa","Baraya","Barbacoas","Barbosa","Barbosa (Santander)","Barichara",
        "Barranca de Upía","Barrancabermeja","Barrancas","Barranco de Loba",
        "Barranquilla","Becerril","Belalcázar","Bello","Belmira","Beltrán","Belén",
        "Belén (Boyacá)","Belén de Bajirá","Belén de Umbría","Belén de los Andaquíes",
        "Berbeo","Betania","Betéitiva","Betulia (Antioquia)","Betulia (Santander)",
        "Bituima","Boavita","Bochalema","Bogotá","Bojacá","Bojayá","Bolívar (Cauca)",
        "Bolívar (Santander)","Bolívar (Valle)","Bosconia","Boyacá","Briceño (Antioquia)",
        "Briceño (Boyacá)","Briceño (Cundinamarca)","Bucaramanga","Bucarasica",
        "Buenaventura","Buenos Aires","Buenavista (Boyacá)","Buenavista (Córdoba)",
        "Buenavista (Quindío)","Buenavista (Sucre)","Bugalagrande","Burítica","Busbanzá",
        "Cabrera (Cundinamarca)","Cabrera (Santander)","Cabuyaro","Cacahual","Cachipay",
        "Caicedo","Caicedonia","Caimito","Cajamarca","Cajibío","Cajicá",
        "Calamar (Bolívar)","Calamar (Guaviare)","Calarcá",
        "Caldas (Antioquia)","Caldas (Boyacá)","Caldas (Cundinamarca)","Caldono",
        "California","Calima Darién","Caloto","Campamento","Campoalegre","Campohermoso",
        "Cali","Canalete","Candelaria (Atlántico)","Candelaria (Valle)","Cantagallo",
        "Cantón de San Pablo","Caparrapí","Capitanejo","Cáqueza","Caracolí","Caramanta",
        "Carcasí","Carepa","Carmen de Apicalá","Carmen de Carupa","Carmen de Viboral",
        "Carmen del Darién","Carolina","Cartagena de Indias","Cartago","Carurú","Casabianca",
        "Castilla la Nueva","Caucasia","Cañasgordas","Cepitá","Cereté","Cerinza","Cerrito",
        "Cerro San Antonio","Cértegui","Chachagüí","Chaguaní","Chalán","Chaparral","Charalá",
        "Charta","Chía","Chigorodó","Chima (Santander)","Chimá (Córdoba)","Chimichagua",
        "Chinavita","Chinchiná","Chinú","Chipaque","Chipatá","Chiquinquirá","Chiriguaná",
        "Chiscas","Chita","Chitagá","Chitaraque","Chivatá","Chivolo","Choachí",
        "Chocontá","Cicuco","Ciénaga (Magdalena)","Ciénaga de Oro","Cimitarra",
        "Cúcuta","Circasia","Cisneros","Clemencia","Cocorná","Coello","Cogua",
        "Colombia","Colón (Putumayo)","Colón (Nariño)","Coloso","Cómbita",
        "Concepción (Antioquia)","Concepción (Santander)","Concordia (Antioquia)",
        "Concordia (Magdalena)","Condoto","Confines","Consacá","Contadero",
        "Contratación","Convención","Copacabana","Coper","Cordobá","Corinto",
        "Coromoro","Corozal","Corrales","Cota","Cotorra","Covarachía","Coveñas",
        "Coyaima","Cravo Norte","Cuaspud","Cubarral","Cubará","Cucaita","Cucunubá",
        "Cucutilla","Cumaral","Cumaribo","Cumbal","Cumbitara","Cunday","Curillo",
        "Curití","Curumaní","Cáceres","Dabeiba","Dagua","Dibulla","Distracción",
        "Dolores","Don Matías","Dosquebradas","Duitama","Durania","Ebéjico","El Águila",
        "El Bagre","El Banco","El Cairo","El Calvario","El Carmen (Norte de Santander)",
        "El Carmen de Atrato","El Carmen de Bolívar","El Castillo","El Cerrito","El Charco",
        "El Cocuy","El Colegio","El Copey","El Doncello","El Dorado","El Dovio",
        "El Encanto","El Espino","El Guacamayo","El Guamo","El Litoral del San Juan",
        "El Molino","El Paso","El Paujil","El Peñol","El Peñón (Bolívar)","El Peñón (Santander)",
        "El Peñón (Cundinamarca)","El Piñón","El Playón","El Retorno","El Retiro","El Roble",
        "El Rosal","El Rosario","El Tablón de Gómez","El Tambo (Cauca)","El Tambo (Nariño)",
        "El Tarra","El Yopal","El Zulia","Encino","Enciso","Entrerríos","Envigado","Espinal",
        "Facatativá","Falan","Filadelfia","Filandia","Firavitoba","Flandes","Florencia","Floresta",
        "Florida","Floridablanca","Florián","Fonseca","Fortúl","Fosca","Fómeque","Francisco Pizarro",
        "Fredonia","Fresno","Frontino","Fuente de Oro","Fundación","Funes","Funza","Fusagasugá",
        "Gachalá","Gachancipá","Gachantivá","Gachetá","Galapa","Galeras","Gama","Gamarra",
        "Garagoa","Garzón","Gigante","Ginebra","Giraldo","Girardot","Girardota","Girón",
        "Granada (Antioquia)","Granada (Meta)","Granada (Cundinamarca)","Guaca","Guacamayas",
        "Guacarí","Guachetá","Guarne","Guasca","Guatapé","Guatavita","Guayabal de Síquima",
        "Guayatá","Guepsa","Hacarí","Heliconia","Hispania","Honda","Ibagué","Icononzo",
        "Ipiales","Istmina","Itagüí","Ituango","Jamundí","Jardín","Jenésano","Jericó",
        "La Calera","La Ceja","La Cruz","La Cumbre","La Dorada","La Estrella","La Jagua de Ibirico",
        "La Macarena","La Mesa","La Palma","La Paz (Cesar)","La Plata","La Vega (Cundinamarca)",
        "La Victoria (Valle)","La Virginia","Líbano","Lloró","Lorica","Los Patios","Luruaco",
        "Madrid","Magangué","Maicao","Malambo","Manizales","Manzanares","Margarita",
        "Marinilla","Mariquita","Marsella","Medellín","Melgar","Mercaderes","Mesetas",
        "Miranda","Mocoa","Mompox","Moniquirá","Monterrey","Montería","Montenegro",
        "Morales (Bolívar)","Mosquera (Cundinamarca)","Neiva","Ocaña","Palmira","Pamplona",
        "Pasto","Pereira","Piedecuesta","Pitalito","Popayán","Quibdó","Riohacha","Santa Marta",
        "Sincelejo","Soacha","Sogamoso","Tuluá","Tunja","Valledupar","Villavicencio","Yopal",
        "Amazonas","Antioquia","Arauca","Atlántico","Bolívar","Boyacá","Caldas","Caquetá",
        "Casanare","Cauca","Cesar","Chocó","Cundinamarca","Córdoba","Guainía","Guaviare",
        "Huila","La Guajira","Magdalena","Meta","Nariño","Norte de Santander","Putumayo",
        "Quindío","Risaralda","San Andrés, Providencia y Santa Catalina","Santander",
        "Sucre","Tolima","Valle del Cauca","Vaupés","Vichada"] 

    ciudades_norm = [c.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
                     for c in ciudades]
    mapa = dict(zip(ciudades_norm, ciudades))

    for w in norm.split():
        if w in mapa: return mapa[w]
    return mapa.get(norm)



def extract_budget(text):
    text = limpiar_trigger(text)
    text = text.lower().replace(".", "").replace(",", "").strip()

    m = re.search(r"(\d+)\s*millones?", text)
    if m: return int(m.group(1)) * 1_000_000

    nums = re.sub(r"\D", "", text)
    if nums.isdigit() and len(nums) >= 4:
        return int(nums)

    return None


def extract_phone(text):
    text = limpiar_trigger(text)
    phone = re.sub(r"\D", "", text)
    return phone if 7 <= len(phone) <= 12 else None


# ==============================================
# MODELLO DE INTENTOS Y SEMÁNTICA
# ==============================================
intent_model = joblib.load("models/intent_model.joblib")
vectorizer = joblib.load("models/intent_vectorizer.joblib")

emb = torch.load("semantic_embeddings.pt")
model_sem = SentenceTransformer("all-MiniLM-L6-v2")

with open("intents_v2.json","r",encoding="utf-8") as f:
    intents = json.load(f)["intents"]


def find_semantic(text):
    q = model_sem.encode(text, convert_to_tensor=True)
    scores = torch.matmul(q, emb["sentence_embeddings"].T)
    idx = torch.argmax(scores).item()
    tag = emb["mapping"][idx]
    return next((i for i in intents if i["tag"] == tag), None)


# ==============================================
# CONFIRMACIÓN DE DATOS
# ==============================================
def confirm_value(field, value, state):
    state["confirming"] = field
    return f"¿Tu {field} es {value}? (sí / no)"


def process_confirmation(msg, state):
    msg = limpiar_trigger(msg).lower().strip()
    field = state.get("confirming")

    if not field: return "No entendí, repite por favor."

    if msg in ["si","sí","claro","correcto","ok"]:
        state["confirming"] = None

        if field == "nombre":
            state["last_action"]="save_city"
            return f"Genial {state['name']} 😊 ¿De qué ciudad nos escribes?"

        if field == "ciudad":
            if state["modo"]=="invertir":
                state["last_action"]="save_budget"
                return f"{state['name']}, ¿cuál es tu presupuesto? Ej: 5 millones"
            else:
                state["last_action"]="save_phone"
                return f"{state['name']} ¿tu número de WhatsApp?"

        if field=="presupuesto":
            state["last_action"]="save_phone"
            return f"Perfecto 💰 ahora dame tu número de WhatsApp."

        if field=="teléfono":
            guardar_en_google_sheets(
                modo=state["modo"], name=state["name"], city=state["city"],
                budget=state["budget"], phone=state["phone"]
            )
            return f"✔ Registro guardado.\nUn asesor te contactará pronto 📩"

    state[field]=None
    state["confirming"]=None
    return f"Ok, repíteme tu {field}."


# ==============================================
# MANEJO POR ETAPAS NOMBRE / CIUDAD / PRESUPUESTO / TELÉFONO
# ==============================================
def handle_action(msg, state):
    msg = limpiar_trigger(msg).lower().strip()

    if state["confirming"]:
        return process_confirmation(msg, state)
        
    if state["last_action"]=="save_name":
        n=extract_name(msg)
        if n: state["name"]=n; return confirm_value("nombre",n,state)
        return "No entendí tu nombre 🙈"

    if state["last_action"]=="save_city":
        c=extract_city(msg)
        if c: state["city"]=c; return confirm_value("ciudad",c,state)
        return "No reconocí la ciudad 🤔 intenta escribiendo solo *Cali*"

    if state["last_action"]=="save_budget":
        b=extract_budget(msg)
        if b: state["budget"]=b; return confirm_value("presupuesto",f"${b:,}",state)
        return "Dime tu presupuesto así:\n**5 millones** o **5000000**"

    if state["last_action"]=="save_phone":
        p=extract_phone(msg)
        if p: state["phone"]=p; return confirm_value("teléfono",p,state)
        return "Escribe tu número sin espacios. Ej: 3141234567"


# ==============================================
#  ⚡ CHATBOT PRINCIPAL (CORRECTO Y FINAL)
# ==============================================
def chatbot(msg, state):
    m = msg.lower().strip()

    if "asesor" in m:
        return "Contacto directo 👇 https://wa.me/573160422795"

    if state["modo"] is None:
        if "aprender" in m:
            state["modo"]="aprender"; state["last_action"]="save_name"
            return "Perfecto 🤓 ¿Cuál es tu nombre completo?"
        if "invertir" in m:
            state["modo"]="invertir"; state["last_action"]="save_name"
            return "Excelente 💼 ¿Tu nombre completo?"
        return "¿Deseas *aprender* o *invertir*? 🤔"

    if state["confirming"]:
        return process_confirmation(msg, state)

    if state["last_action"]:
        forced = handle_action(msg, state)
        if forced: return forced

    cleaned = clean_text(msg)
    intent = intent_model.predict(vectorizer.transform([cleaned]))[0]

    for i in intents:
        if i["tag"] == intent:
            state["last_action"] = i.get("next_action")
            r = i["responses"][0]
            return (r.replace("{name}", state["name"] or "")
                     .replace("{city}", state["city"] or "")
                     .replace("{budget}", f"${state['budget']:,}" if state["budget"] else "")
                     .replace("{phone}", state["phone"] or ""))

    sem = find_semantic(msg)
    if sem:
        state["last_action"]=sem.get("next_action")
        return sem["responses"][0]

    return "No logré entenderte 😅 prueba con otras palabras o escribe *asesor*."


# ==============================================
# ⚡ ENDPOINT PARA MANYCHAT / INSTAGRAM
# ==============================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data=request.get_json(force=True)

    uid=str(data.get("user_id") or data.get("sender_id") or 
            data.get("contact_id") or data.get("profile_id") or "anon")

    msg=data.get("message") or data.get("text") or data.get("comment") or ""

    state=get_state(uid)
    respuesta=chatbot(msg,state)

    return jsonify({"respuesta":respuesta}),200


@app.route("/",methods=["GET"])
def home():
    return {"status":"online"},200


if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)



