from flask import Flask, request, jsonify
import json
import torch
import joblib
from clean_text import clean_text
from sentence_transformers import SentenceTransformer
import re

app = Flask(__name__)

# -----------------------------
# ESTADO DEL USUARIO
# -----------------------------
user_state = {
    "name": None,
    "city": None,
    "budget": None,
    "phone": None,
    "modo": None,
    "last_action": None,
    "confirming": None
}

# -----------------------------
# EXTRACCIÓN DE NOMBRE
# -----------------------------
def extract_name(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Záéíóúñ ]", "", text)
    match = re.search(r"(me llamo|mi nombre es|soy)\s+([a-zA-Záéíóúñ ]+)", text)

    if match:
        name = match.group(2).strip()
        if 1 <= len(name.split()) <= 3:
            return name.title()

    if 1 <= len(text.split()) <= 3:
        return text.title()
    return None

# -----------------------------
# EXTRACCIÓN CIUDAD — (tu lista completa)
# -----------------------------
def extract_city(text):
    text = text.lower()
    text = re.sub(r"(desde|soy de|estoy en|vivo en|ciudad de|de|en)\s+", "", text)

    norm = text.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")

    # ⬇ USO TU LISTA TAL CUAL
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
        "Santander", "Sucre", "Tolima", "Valle del Cauca", "Vaupés", "Vichada", "popayán" ]

    ciudades_norm = [c.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
                     for c in ciudades]
    mapa = dict(zip(ciudades_norm, ciudades))

    for w in norm.split():
        if w in mapa: return mapa[w]
    return mapa.get(norm)

# -----------------------------
# EXTRACCIÓN PRESUPUESTO
# -----------------------------
def extract_budget(text):
    text = text.lower().replace(".", "").replace(",", "").strip()
    match = re.search(r"(\d+)\s*millones?", text)
    if match: return int(match.group(1)) * 1_000_000

    nums = re.sub(r"\D", "", text)
    if nums.isdigit() and len(nums) >= 4: return int(nums)
    return None

# -----------------------------
# EXTRACCIÓN TELÉFONO
# -----------------------------
def extract_phone(text):
    phone = re.sub(r"\D", "", text)
    return phone if 7 <= len(phone) <= 12 else None

# -----------------------------
# MODELOS
# -----------------------------
intent_model = joblib.load("models/intent_model.joblib")
vectorizer = joblib.load("models/intent_vectorizer.joblib")

emb = torch.load("semantic_embeddings.pt")
model_sem = SentenceTransformer("all-MiniLM-L6-v2")

with open("intents_v2.json","r",encoding="utf-8") as f:
    intents = json.load(f)["intents"]

# -----------------------------
# SEMÁNTICA
# -----------------------------
def find_semantic(text):
    q = model_sem.encode(text, convert_to_tensor=True)
    idx = torch.argmax(torch.matmul(q, emb["sentence_embeddings"].T)).item()
    tag = emb["mapping"][idx]
    return next((i for i in intents if i["tag"] == tag), None)

# -----------------------------
# CONFIRMACIÓN
# -----------------------------
def confirm_value(field,value):
    user_state["confirming"]=field
    return f"¿Tu {field} es {value}? (sí / no)"

def process_confirmation(msg):
    msg = msg.lower().strip()

    if msg in ["si","sí","claro","correcto","ok"]:
        field=user_state["confirming"]
        user_state["confirming"]=None

        if field=="nombre":
            user_state["last_action"]="save_city"
            return f"Listo {user_state['name']} 😊 ¿De qué ciudad nos escribes?"

        if field=="ciudad":
            if user_state["modo"]=="invertir":
                user_state["last_action"]="save_budget"
                return f"{user_state['name']}, ¿cuál es tu presupuesto para invertir?"
            else:
                user_state["last_action"]="save_phone"
                return f"{user_state['name']}, ¿tu número de teléfono?"

       
       if field == "presupuesto":
    user_state["last_action"] = "save_phone"
    return (
        f"Excelente {user_state['name']} 💰\n"
        "Ahora dime tu número de WhatsApp para contactarte."
    )




        if field=="teléfono":
            from google_sheets import guardar_en_google_sheets
            guardar_en_google_sheets(
                modo=user_state["modo"],
                name=user_state["name"],
                city=user_state["city"],
                budget=user_state["budget"],
                phone=user_state["phone"]
            )
            return f"Perfecto {user_state['name']} 😊\nRegistro completado.\nUn asesor te contactará al {user_state['phone']} 📩"

    # ❗Si dice "no"
    invalid=user_state["confirming"]
    user_state[invalid]=None
    user_state["confirming"]=None
    return f"Ok, repíteme tu {invalid}"

# -----------------------------
# MANEJO DE ETAPAS
# -----------------------------
def handle_action(msg):
    if user_state["confirming"]: return process_confirmation(msg)

    if user_state["last_action"]=="save_name":
        n=extract_name(msg)
        if n: user_state["name"]=n; return confirm_value("nombre",n)
        return "No entendí tu nombre 🙈 intentemos otra vez."

    if user_state["last_action"]=="save_city":
        c=extract_city(msg)
        if c: user_state["city"]=c; return confirm_value("ciudad",c)
        return "No pude identificar la ciudad 🤔 escribe otra vez."

    if user_state["last_action"]=="save_budget":
        b=extract_budget(msg)
        if b: user_state["budget"]=b; return confirm_value("presupuesto",f"${b:,}")
        return "No entendí tu presupuesto. Ej: 5 millones / 5000000"

    if user_state["last_action"]=="save_phone":
        p=extract_phone(msg)
        if p: user_state["phone"]=p; return confirm_value("teléfono",p)
        return "Ese número no parece válido 📵 envíalo de nuevo."

# -----------------------------
# CHATBOT CENTRAL
# -----------------------------
def chatbot(msg):

    m=msg.lower().strip()

    # 🟢 Primer paso: aprender o invertir
    if user_state["modo"] is None:
        if "aprender" in m: user_state["modo"]="aprender"; user_state["last_action"]="save_name"; return "Perfecto 🤓 empecemos. ¿Tu nombre?"
        if "invertir" in m: user_state["modo"]="invertir"; user_state["last_action"]="save_name"; return "Excelente 💼 ¿Tu nombre completo?"
        return "¿Deseas *aprender* o *invertir*? 🤔"

    if "asesor" in m: return "Contacto directo 👇 https://wa.me/573160422795"

    if user_state["confirming"]:
        return process_confirmation(msg)

    if user_state["last_action"]:
        return handle_action(msg)

    # INTENTOS Y RESPUESTAS
    cleaned=clean_text(msg)
    intent=intent_model.predict(vectorizer.transform([cleaned]))[0]

    for i in intents:
        if i["tag"]==intent:
            user_state["last_action"]=i.get("next_action")
            r=i["responses"][0]

            if "{name}" in r: r=r.replace("{name}",user_state["name"] or "")
            if "{city}" in r: r=r.replace("{city}",user_state["city"] or "")
            if "{budget}" in r: r=r.replace("{budget}",f"${user_state['budget']:,}" if user_state["budget"] else "")
            if "{phone}" in r: r=r.replace("{phone}",user_state["phone"] or "")

            return r

    sem=find_semantic(msg)
    if sem:
        user_state["last_action"]=sem.get("next_action")
        return sem["responses"][0]

    return "No logré entenderte 😅 prueba con otras palabras."

# -----------------------------
# ENDPOINT WEB (INSTAGRAM/MANYCHAT)
# -----------------------------
@app.route("/webhook",methods=["POST"])
def webhook():
    data=request.get_json(force=True)
    msg=data.get("message") or data.get("text") or data.get("comment") or ""
    return jsonify({"respuesta": chatbot(msg)}),200

@app.route("/",methods=["GET"])
def home():
    return {"status":"online"},200

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)


