import os
from flask import Flask, request, jsonify
import json
import joblib
import re
from clean_text import clean_text
from google_sheets import guardar_en_google_sheets  # si no usarás Sheets, comenta esta línea
import requests


def contains_word(text: str, word: str) -> bool:
    text = (text or "").lower()
    return re.search(rf"\b{re.escape(word.lower())}\b", text) is not None





GHL_WEBHOOK_URL = os.getenv("GHL_WEBHOOK_URL")

def enviar_a_ghl(state, uid):
    if not GHL_WEBHOOK_URL:
        print("❌ GHL_WEBHOOK_URL no configurada")
        return

    payload = {
        "external_user_id": uid,
        "name": state.get("name"),
        "phone": state.get("phone"),
        "city": state.get("city"),
        "modo": state.get("modo"),
        "estado_lead": "listo_para_invertir",
        "source": "instagram_bot"
    }

    try:
        r = requests.post(GHL_WEBHOOK_URL, json=payload, timeout=10)
        print("✅ Enviado a GHL:", r.status_code)
    except Exception as e:
        print("❌ Error enviando a GHL:", e)


app = Flask(__name__)

# ==============================================
#    CONTROL DE ESTADO POR USUARIO (CORRECTO)
# ==============================================
user_states = {}

def reset_state(state):
    state.clear()
    state.update({
        "name": None,
        "city": None,
        "phone": None,
        "modo": None,
        "last_action": None,
        "confirming": None
    })

def get_state(uid):
    if uid not in user_states:
        user_states[uid] = {
            "name": None,
            "city": None,
            "phone": None,
            "modo": None,
            "last_action": None,
            "confirming": None,
            "completed": False,
            "welcomed": False
        }
    return user_states[uid]

# ==============================================
#  📌  EXTRACCIÓN DE DATOS DEL USUARIO
# ==============================================

def extract_name(text):
    if not text:
        return None

    # Normalización inicial
    text = text.lower().strip()   
    text = re.sub(r"[^a-záéíóúñ ]", "", text)

    invalid = [
        "invertir","aprender","si","no","ok","vale","listo","claro","gracias"
    ]

    if text in invalid:
        return None

    # Buscar expresiones comunes
    match = re.search(r"(me llamo|mi nombre es|soy)\s+(.*)", text)
    if match:
        name = match.group(2).strip()
    else:
        # si no hay patrón, usar todo el texto
        name = text

    # separo por palabras
    parts = name.split()

    # si no hay partes válidas
    if not parts:
        return None

    # tomar solo el primer nombre
    primer_nombre = parts[0]

    # capitalizar bonito
    return primer_nombre.title()


def extract_city(text):
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
        "Carmen del Darién","Carolina","Cartagena de Indias","cartagena","Cartago","Carurú","Casabianca",
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
        "Sucre","Tolima","Valle del Cauca","Vaupés","Vichada","Buga", "Alcalá", "Andersen", "Buga", "Bugalagrande", "Bolívar", 
        "Buenaventura", "Cali", "Calima", "Candelaria", "Cartago", "Dagua", "El Águila", "El Cairo", 
        "El Cerrito", "El Dovio", "Florida", "Galeras", "Ginebra", "Guacarí", "Guachené", "Jamundí", 
        "La Cumbre", "La Unión", "La Victoria", "Obando", "Palmira", "Pradera", "Restrepo", "Riofrío", "Roldanillo",
        "San Jerónimo", "San Juan del Valle", "San Pedro", "Santa Bárbara", "Santa Cruz", "Sevilla", "Toro", 
        "Tuluá", "Ulloa", "Uncía", "Versalles", "Vijes"
] 

    ciudades_norm = [c.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
                     for c in ciudades]
    mapa = dict(zip(ciudades_norm, ciudades))

    for w in norm.split():
        if w in mapa: return mapa[w]
    return mapa.get(norm)


def extract_phone(text):
    if not text:
        return None
    
    # quitar todo lo que no sea número
    phone = re.sub(r"\D", "", text)
    if not phone:
        return None

    if phone.startswith("57") and len(phone) == 12:
        return "+57" + phone[2:]

    # Caso 2: viene solo el número colombiano (10 dígitos)
    if len(phone) == 10 and phone.startswith("3"):
        return "+57" + phone

     # Caso 3: número internacional (7 a 15 dígitos)
    if 7 <= len(phone) <= 15:
        return "+" + phone

    return None

    
# ==============================================
# MODELLO DE INTENTOS Y SEMÁNTICA
# ==============================================
intent_model = joblib.load("models/intent_model.joblib")
vectorizer = joblib.load("models/intent_vectorizer.joblib")

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

def process_confirmation(msg, state, uid):
    msg = msg.lower().strip()
    field = state.get("confirming")

    if not field:
        return "No entendí, repite por favor."

    # Respuestas afirmativas
    afirm = ["si","sí","claro","correcto","ok","sisas","s","dale","perfecto","todo bien","así está bien"]

    # Respuesta negativa
    neg = ["no","nop","nel","nope","ño","n"]
    
    if msg in afirm: 
        state["confirming"] = None
        
        if field == "nombre":
            state["last_action"] = "save_city"
            return f"Genial {state['name']} 😊 ¿De qué ciudad nos escribes?"

        if field == "ciudad":
           state["last_action"] = "save_phone"
           return (
            f"{state['name']} 📱 regálame tu número de WhatsApp.\n"
            "Ejemplo:\n"
            "3053662888"
           )

        if field == "telefono":
           try:
               guardar_en_google_sheets(
                   modo=state["modo"],
                   name=state["name"],
                   city=state["city"],
                   phone=state["phone"]
               )
           except:
               pass

           if state["modo"] == "invertir":
                 enviar_a_ghl(state, uid)

           state.update({
                "name": None,
                "city": None,
                "phone": None,
                "modo": None,
                "last_action": None,
                "confirming": None,
                "completed": True
            })


            


           return (
                  "Perfecto ✔️ Registro guardado.\n"
                  "Un asesor te contactará pronto 💌\n\n"
            )



        return "Listo."
        
    if msg in neg: 
        state["confirming"] = None

        if field == "nombre":
            state["last_action"] = "save_name"
            return "Vale, dime de nuevo tu nombre completo 😊"

        if field == "ciudad":
            state["last_action"] = "save_city"
            return "Listo, escribe de nuevo tu ciudad."

        if field == "telefono":
            state["last_action"] = "save_phone"
            return "Ok, escríbeme de nuevo tu número de WhatsAp."

        return f"Ok, repíteme tu {field}."

    # si responde algo raro #
    
    
    
    
  
# ==============================================
# MANEJO POR ETAPAS NOMBRE / CIUDAD / TELÉFONO
# ==============================================
def handle_action(msg, state, uid):
    nombre = state.get("name") or ""


    if state["confirming"]:
        return process_confirmation(msg, state, uid)
        
    # ==========================
    # ----- Guardar nombre -----
    # ==========================
    if state["last_action"]=="save_name":
        n=extract_name(msg)
        
        if n: 
            state["name"]=n 
            state["last_action"] = "save_city"
            return f"Perfecto {n} 😊 ¿De qué ciudad nos escribes?"
            
        return (
            "No entendí tu nombre 🤔 Escríbelo nuevamente, por favor."
        )

    # ==========================
    # ..... Guardar ciudad .....
    # ==========================
    if state["last_action"]=="save_city":
        c=extract_city(msg)
        
        if c: 
            state["city"]=c
            state["confirming"] = "ciudad"
            return (
                  f"Genial 🙌 entonces estás en *{c}*. Confirmame con (si/no) ✍️"
                   )
            
        return "No reconocí la ciudad 🤔 intenta escribiendo solo tu ciudad"

    # ==========================
    # ---- GUARDAR TELEFONO -----
    # ========================== 
    if state["last_action"] == "save_phone":
        p = extract_phone(msg)

        if p:
            state["phone"] = p
            state["confirming"] = "telefono"
            return (
                   f"Perfecto {state['name']}, ¿este es tu número? {p}"

            )


        return (
            f"{state['name']} 📱 escríbeme tu número de WhatsApp.\n"
            "Ejemplo: 3053662888\n"
        )

    return None

# ==============================================
#  ⚡ CHATBOT PRINCIPAL (CORRECTO Y FINAL)
# ==============================================
def chatbot(msg, state, uid):
# ======================================================
#  BLOQUEO TOTAL SI EL FLUJO YA TERMINÓ
# ======================================================
    if state.get("completed"):
        return ""

    
    m = msg.lower().strip()

    # ======================================================
    #  CANCELAR
    # ======================================================
    if "cancel" in m or "cancelar" in m:
        state.update({
            "name": None,
            "city": None,
            "phone": None,
            "modo": None,
            "last_action": None,
            "confirming": None
        })
        return "Proceso cancelado. Volvamos a empezar 😊 ¿Deseas aprender o invertir?"

    # ======================================================
    #  ACCESO DIRECTO A ASESOR
    # ======================================================
    if "asesor" in m or "asesoria" in m:
        return "Contacto directo 👇 https://wa.me/573160422795"

    # ======================================================
    #  SI NO HAY MODO DEFINIDO TODAVÍA
    # ======================================================
    if state["modo"] is None:

         if not state.get("welcomed"):
             state["welcomed"] = True
             return (
                "✨ ¡Hola! Qué alegría tenerte por aquí ✨\n"
                "👋 Somos Grupo T. Vimos tu interés sobre remates hipotecarios.\n"
                "Ahora dime, ¿Deseas *aprender* o *invertir*? 🤔"
             )

        # Caso: menciona ambas
    
          if contains_word(m, "invertir"):
              state["modo"] = "invertir"
              state["last_action"] = "save_name"
              return "Excelente 💼 vamos a registrar tus datos para que te comuniques con uno de nuestros asesores ¿Cuál es tu nombre completo?✨"

          if contains_word(m, "aprender"):
              state["modo"] = "aprender"
              state["last_action"] = "save_name"
              return "Excelente 💼 vamos a registrar tus datos para que te comuniques con uno de nuestros asesores ¿Cuál es tu nombre completo?✨"

         if "las dos" in m or "ambas" in m:
              state["modo"] = "invertir"
              state["last_action"] = "save_name"
              return "Excelente 💼 vamos a registrar tus datos para que te comuniques con uno de nuestros asesores ¿Cuál es tu nombre completo?✨"

         return None

    # ======================================================
    #  MODO APRENDER — TU COMPAÑERO MANEJA ESTO EN MANYCHAT
    # ======================================================
    if state["modo"] == "aprender":
        return "Un asesor te contactará directamente para aprendizaje 😊"

    # ======================================================
    #  MODO INVERTIR — FLUJO ACTIVO
    # ======================================================

    # Confirmación pendiente
    if state["confirming"]:
        return process_confirmation(msg, state, uid)

    # Manejo de etapas (nombre, ciudad, teléfono)
    if state["last_action"]:
        forced = handle_action(msg, state, uid)
        if forced:
            return forced

    # ======================================================
    #  SI LLEGA AQUÍ Y SIGUE EN MODO INVERTIR → NO USAR INTENTS
    #  EVITAMOS RESPUESTAS RARAS.
    # ======================================================
    return (
        "Estamos avanzando con tu registro de inversión.\n"
        "Por favor continúa donde íbamos o escribe tu nombre."
    )


# ==============================================
# ⚡ ENDPOINT PARA MANYCHAT / INSTAGRAM
# ==============================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True) or {}

    uid = str(
        data.get("user_id")
        or data.get("sender_id")
        or data.get("contact_id")
        or data.get("profile_id")
        or "anon"
    )

    raw_msg = data.get("message") or data.get("text") or data.get("comment") or ""

    # Blindaje total
    if isinstance(raw_msg, dict):
        msg = raw_msg.get("body") or raw_msg.get("text") or ""
    else:
        msg = str(raw_msg)

    state = get_state(uid)
    respuesta = chatbot(msg, state, uid)

    # 👇 CLAVE PARA GOHIGHLEVEL
    return jsonify({
        "success": True,
        "respuesta": respuesta
    }), 200



@app.route("/",methods=["GET"])
def home():
    return {"status":"online"},200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)














