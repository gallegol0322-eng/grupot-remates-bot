import os
from flask import Flask, request, jsonify
import json
import joblib
import re
from clean_text import clean_text
from google_sheets import guardar_en_google_sheets  # si no usarás Sheets, comenta esta línea
import requests
import traceback



def contains_any(text: str, words: list) -> bool:
    text = (text or "").lower()
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


INVERTIR_KEYWORDS = [
    "invertir", "adquirir", "propiedad", "comprar", "inversion", "casa", "apartamento","remates","comprar","las dos", "ambas", "dos", "todo", "todo junto"
]
APRENDER_KEYWORDS = [
    "aprender", "mentoria", "mentor", "enseñar", "estudiar", "curso", "clases"
]


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
        "estado_lead": state.get("estado_lead"),
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
            "completed": False,
            "locked": False,
            "welcomed": False
        }
    return user_states[uid]

# ==============================================
#  📌  EXTRACCIÓN DE DATOS DEL USUARIO
# ==============================================

def extract_name(text):
    if not text:
        return "No reconozco tu nombre"

    # Normalización inicial
    text = text.lower().strip()   
    text = re.sub(r"[^a-záéíóúñ ]", "", text)

    for w in INVERTIR_KEYWORDS + APRENDER_KEYWORDS:
        if re.search(rf"\b{re.escape(w)}\b", text):
            return ""

    invalid = [
        "invertir","aprender","si","no","ok","vale","listo","claro","gracias","mentoria"
    ]

    if text in invalid:
        return ""

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
        return ""

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
        return ""
    
    # quitar todo lo que no sea número
    phone = re.sub(r"\D", "", text)
    if not phone:
        return ""

    if phone.startswith("57") and len(phone) == 12:
        return "+57" + phone[2:]

    # Caso 2: viene solo el número colombiano (10 dígitos)
    if len(phone) == 10 and phone.startswith("3"):
        return "+57" + phone

     # Caso 3: número internacional (7 a 15 dígitos)
    if 7 <= len(phone) <= 15:
        return "+" + phone

    return ""

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
           enviar_a_ghl(state, uid)
               
           state["completed"] = True
            
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
            state["last_action"] = "save_phone"
            return (
                  f"{state['name']} 📱 escríbeme tu número de WhatsApp.✍️\n"
                  "Ejemplo: 3053662888"
                   )
            
        return "No reconocí la ciudad 🤔 intenta escribiendo solo tu ciudad"

    # ==========================
    # ---- GUARDAR TELEFONO -----
    # ========================== 
    if state["last_action"] == "save_phone":
        p = extract_phone(msg)
        if p:
            state["phone"] = p

            try: 
                guardar_en_google_sheets(
                modo=state["modo"],
                name=state["name"],
                city=state["city"],
                phone=state["phone"]
            )

            except:
                pass

            enviar_a_ghl(state, uid)

            state["completed"] = True
            state["locked"] = True

            return (
                 "Perfecto ✔️ Registro guardado.💌\n"
                 "Un asesor se pondrá en contacto contigo en breve 💼📞"
            )



        return "Ese número no parece válido, escríbelo nuevamente."


# ==============================================
#  ⚡ CHATBOT PRINCIPAL (CORRECTO Y FINAL)
# ==============================================
def chatbot(msg, state, uid):
# ======================================================
#  BLOQUEO TOTAL SI EL FLUJO YA TERMINÓ
# ======================================================
    if state.get("locked"):
      return "📒 Ya tenemos tus datos. Un asesor te contactará pronto. ✅"

    m = msg.lower().strip()

    if m == "desbloquear":
      state.update({
        "locked": False,
        "completed": False,
        "modo": None,
        "estado_lead": None,
        "last_action": None,
        "confirming": None,
        "welcomed": False
      })

      return "🔓 Chat desbloqueado. ¿Deseas invertir o mentoría?"
            

    # ======================================================
    #  CANCELAR
    # ======================================================
    if "cancel" in m or "cancelar" in m:
        state.update({
            "name": None,
            "city": None,
            "phone": None,
            "modo": None,
            "estado_lead": None,
            "last_action": None,
            "confirming": None,
            "completed": False,
            "locked": False,
            "welcomed": False

        })
        return "Proceso cancelado. Volvamos a empezar 😊 ¿Deseas mentoria o invertir?"

    # ======================================================
    #  ACCESO DIRECTO A ASESOR
    # ======================================================
    if "asesor" in m or "asesoria" in m:
        return "Contacto directo con un asesor 👇 https://wa.me/573160422795"
    # ======================================================
    #  SI NO HAY MODO DEFINIDO TODAVÍA
    # ======================================================
    # ======================================================
#  SI NO HAY MODO DEFINIDO TODAVÍA
# ======================================================
    if state["modo"] is not None and state.get("last_action") is not None:
        forced = handle_action(msg, state, uid)
        if forced:
           return forced

    if state["modo"] is None:
      if contains_any(m, INVERTIR_KEYWORDS):
        state["modo"] = "invertir"
        state["estado_lead"] = "listo_para_invertir"
      elif contains_any(m, APRENDER_KEYWORDS):
        state["modo"] = "mentoria"
        state["estado_lead"] = "listo_para_mentoria"
      else:
        if not state.get("welcomed"):
            state["welcomed"] = True
            return (
                "✨ ¡Hola! Qué alegría tenerte por aquí ✨\n"
                "👋 Somos Grupo T. Vimos tu interés sobre Remates Hipotecarios.\n"
                "Ahora dime, ¿Deseas adquirir una propiedad o aprender sobre remates? 🤔"
            )
        return "👋¿Deseas adquirir una propiedad o aprender sobre remates?✨"


    # 👇 ESTO SOLO SE EJECUTA SI YA DEFINIÓ MODO
    if state["last_action"] is None:
       state["last_action"] = "save_name"
    
       return (
         "Excelente 💼 vamos a registrar tus datos para que te comuniques con uno de nuestros asesores.🧾\n"
         "¿Cuál es tu nombre completo? ✨"
    )

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

def get_ghl_uid(data: dict) -> str:
    # En GHL, contact_id suele ser el identificador real del contacto
    cid = data.get("contact_id") or data.get("contactId")
    if cid:
        return str(cid)

    # Fallbacks comunes
    return str(
        data.get("user_id")
        or data.get("sender_id")
        or data.get("profile_id")
        or data.get("conversation_id")
        or data.get("id")
        or "anon"
    )

def extract_message_from_payload(data: dict) -> str:
    """
    GHL puede enviar el texto en varias claves dependiendo del trigger.
    Ajustamos con fallbacks defensivos.
    """
    # 1) Formato típico
    raw = data.get("message") or data.get("text") or data.get("comment") or data.get("body") or ""

    # 2) A veces viene anidado
    if isinstance(raw, dict):
        raw = raw.get("body") or raw.get("text") or raw.get("message") or ""

    # 3) Otros posibles campos
    if not raw:
        raw = data.get("lastMessage") or data.get("incoming_message") or ""

    return str(raw or "").strip()

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # 1) Intentar JSON SIN forzar (si no es JSON, no explota)
        data = request.get_json(silent=True)

        # 2) Si no hay JSON, intentar form-data
        if not data:
            data = request.form.to_dict() if request.form else {}

        # 3) Último fallback: intentar parsear texto bruto (solo para debug)
        if not data:
            raw_body = request.get_data(as_text=True) or ""
            print("DEBUG RAW BODY:", raw_body[:2000])  # evita logs gigantes
            data = {}

        print("DEBUG PAYLOAD KEYS:", list(data.keys())[:50])

        uid = get_ghl_uid(data)
        state = get_state(uid)

        msg = extract_message_from_payload(data)

        # Si no hay mensaje, respondemos OK
        if not msg:
            return jsonify({"success": True, "respuesta": ""}), 200

        respuesta = chatbot(msg, state, uid) or "👋 Por favor responde el mensaje anterior 💬"

        return jsonify({"success": True, "respuesta": respuesta}), 200

    except Exception as e:
        # Esto es lo que necesitamos ver en Railway para arreglarlo de verdad
        print("❌ ERROR EN /webhook:", repr(e))
        print(traceback.format_exc())

        # Respondemos 200 para que GHL no marque Failed mientras debugueamos
        return jsonify({"success": True, "respuesta": ""}), 200


@app.route("/",methods=["GET"])
def home():
    return {"status":"online"},200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)






