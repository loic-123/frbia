import re
import csv

def parse_qcm_text(text):
    """
    Parse le texte d'un QCM BIA et extrait les questions avec leurs options.
    
    Args:
        text (str): Texte complet du QCM
    
    Returns:
        list: Liste de listes contenant [question, option_A, option_B, option_C, option_D, reponse_correcte]
    """
    questions_list = []
    
    # Nettoyage du texte
    text = clean_text(text)
    
    # Pattern pour capturer les questions numérotées avec format X.Y
    pattern = r'(\d+\.\d+)\s+(.*?)\s*\n\s*([A-D])[.\s]+(.*?)\s*\n\s*([A-D])[.\s]+(.*?)\s*\n\s*([A-D])[.\s]+(.*?)\s*\n\s*([A-D])[.\s]+(.*?)(?=\n\d+\.\d+|\Z)'
    
    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        if len(match) == 9:
            question_num = match[0]
            question_text = clean_question_text(match[1])
            
            # Créer un dictionnaire pour les options
            options = {}
            options[match[2]] = clean_option_text(match[3])
            options[match[4]] = clean_option_text(match[5])
            options[match[6]] = clean_option_text(match[7])
            options[match[8]] = clean_option_text(match[9])
            
            # Vérifier que nous avons bien A, B, C, D
            if all(letter in options for letter in ['A', 'B', 'C', 'D']):
                if is_valid_question(question_text, options['A'], options['B'], options['C'], options['D']):
                    questions_list.append([
                        f"{question_num} {question_text}",
                        options['A'],
                        options['B'],
                        options['C'],
                        options['D'],
                        ""  # Réponse correcte à déterminer
                    ])
    
    # Si peu de questions trouvées, essayer une approche alternative
    if len(questions_list) < 10:
        questions_list.extend(parse_alternative_format(text))
    
    return remove_duplicates(questions_list)

def parse_alternative_format(text):
    """Parse alternatif pour le format BIA spécifique."""
    questions_list = []
    
    # Diviser le texte en blocs de questions
    blocks = re.split(r'\n(?=\d+\.\d+)', text)
    
    for block in blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) < 5:
            continue
        
        # Recherche du numéro et de la question
        question_line = None
        question_num = ""
        
        for i, line in enumerate(lines):
            match = re.match(r'^(\d+\.\d+)\s+(.*)', line)
            if match:
                question_num = match.group(1)
                question_text = match.group(2)
                question_line = i
                break
        
        if question_line is None:
            continue
        
        # Recherche des options A, B, C, D
        options = {'A': '', 'B': '', 'C': '', 'D': ''}
        
        for line in lines[question_line:]:
            for letter in ['A', 'B', 'C', 'D']:
                # Pattern plus flexible pour les options
                patterns = [
                    rf'^{letter}[.\s]+(.*)',
                    rf'^{letter}\s+(.*)',
                    rf'^{letter}\.\s+(.*)'
                ]
                
                for pattern in patterns:
                    match = re.match(pattern, line)
                    if match:
                        options[letter] = match.group(1).strip()
                        break
                if options[letter]:  # Si on a trouvé cette option, passer à la suivante
                    break
        
        # Vérifier que nous avons toutes les options
        if all(options.values()):
            question_text_full = question_text
            if is_valid_question(question_text_full, options['A'], options['B'], options['C'], options['D']):
                questions_list.append([
                    f"{question_num} {question_text_full}",
                    options['A'],
                    options['B'],
                    options['C'],
                    options['D'],
                    ""
                ])
    
    return questions_list

def clean_text(text):
    """Nettoie le texte pour faciliter l'analyse."""
    # Remplacement des guillemets typographiques par des guillemets standards
    text = re.sub(r"[“”]", '"', text)  # guillemets doubles typographiques
    text = re.sub(r"[‘’]", "'", text)  # apostrophes typographiques
    # Normalisation des espaces mais conservation des sauts de ligne
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    return text

def clean_question_text(text):
    """Nettoie le texte d'une question."""
    text = text.strip()
    # Suppression des caractères parasites
    text = re.sub(r'^[>\s]*', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def clean_option_text(text):
    """Nettoie le texte d'une option de réponse."""
    text = text.strip()
    # Suppression des caractères de formatage
    text = re.sub(r'^[>\s]*', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_valid_question(question, option_a, option_b, option_c, option_d):
    """Vérifie si une question et ses options sont valides."""
    if len(question) < 10:
        return False
    if not all([option_a, option_b, option_c, option_d]):
        return False
    if len(option_a) < 2 or len(option_b) < 2:
        return False
    # Vérification que ce n'est pas du texte de formatage
    formatting_keywords = ['page', 'sur', 'coefficient', 'durée', 'épreuve', 'attention', 'recommandations']
    if any(keyword in question.lower() for keyword in formatting_keywords):
        return False
    return True

def remove_duplicates(questions_list):
    """Supprime les questions en double."""
    seen = set()
    unique_questions = []
    
    for question in questions_list:
        # Utilise les 50 premiers caractères de la question comme clé
        key = question[0][:50].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_questions.append(question)
    
    return unique_questions

def save_to_csv(questions_list, output_file="questions_qcm.csv"):
    """Sauvegarde les questions dans un fichier CSV."""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Question', 'Option A', 'Option B', 'Option C', 'Option D', 'Réponse correcte'])
        writer.writerows(questions_list)
    
    print(f"Questions sauvegardées dans {output_file}")

def parse_qcm_from_word(file_path):
    """
    Parse un fichier Word contenant un QCM et extrait toutes les questions avec leurs options.
    Nécessite: pip install python-docx
    
    Args:
        file_path (str): Chemin vers le fichier Word (.docx)
    
    Returns:
        list: Liste de listes contenant [question, option_A, option_B, option_C, option_D, reponse_correcte]
    """
    try:
        from docx import Document
        
        # Lecture du fichier Word
        doc = Document(file_path)
        
        # Extraction de tout le texte
        full_text = ""
        for paragraph in doc.paragraphs:
            full_text += paragraph.text + "\n"
        
        return parse_qcm_text(full_text)
    
    except ImportError:
        print("Pour lire les fichiers Word, installez python-docx avec: pip install python-docx")
        return []

# Exemple d'utilisation
if __name__ == "__main__":
    document_text = """
    1.1	Une information sur une carte stipule l'ISO 0°C au FL80. Vous devez voler au FL60. En considérant le gradient standard, quelle est la bonne affirmation ?
A Le vol se fera à +4 °C.
B. Le vol se fera à -4 °C.
C. Le vol se fera à -2 °C.
D. Le vol se fera à +2 °C.

1.2	Les deux principaux composants de l'air sec sont :
A le diazote et le dioxygène.
B. l'oxygène et le gaz carbonique.
C. l'azote et l'hélium.
D. l'oxygène et l'hydrogène.

1.3	La transformation de l'eau de l'état gazeux à l'état liquide s'appelle : A la fusion.
B. la sublimation.
C. l'évaporation.
D. la condensation.

1.4	Une trouée de Foehn:
A.	est un endroit favorable à la pratique de la voltige aérienne.
B.	est une trouée de ciel clair associée à l'apparition d'un Cumulonimbus qui capte toute l'humidité de l'air.
C.	est une zone de ciel clair sous le vent d'un relief par suite d'asséchement de la masse d'air.
D.	est une zone de ciel clair liée à de hautes pressions à l'arrière d'un massif montagneux.

1.5	Parmi les éléments suivants, une conséquence possible du givrage est :
A.	un gain d'altitude.
B.	une altération des profils aérodynamiques.
C.	une amélioration des performances de l'aéronef.
D.	une diminution de la traînée.

1.6	Lorsque le vent est fort au sol :
A il y a peu de turbulences dans les basses couches de l'atmosphère.
B. le ciel va systématiquement se dégager.
C. il est nul en altitude.
D. des turbulences dues aux imperfections du sol et aux obstacles se développent en basses couches.
 



1.7	Le mistral est un vent:
A.	du sud sur Marseille.
B.	du sud-ouest qui souffle sur le Languedoc.
C.	du nord-ouest qui souffle sur le Languedoc.
D.	du nord qui souffle dans la vallée du Rhône.

1.8	« Marais barométrique » désigne :
A.	une zone où la pression varie peu.
B.	une zone ou un axe de basses pressions.
C.	une zone ou un axe de hautes pressions.
D.	une zone où le gradient de pression est très élevé.

1.9	Sur la photo ci-dessous, prise à Paris-Orly au lever du jour après une nuit fraîche, sans nuages et sans vent, on observe un brouillard :
A.	d'advection.
B.	de rayonnement.
C.	d'évaporation.
D.	de convection.






1.10	Sur une carte de pression une ligne qui joint les points d'égale pression est nommée :
A.	une isotherme.
B.	une isocline.
C.	une isohypse.
D.	une isobare.
 


1.11	Un front froid :
A.	est une surface séparant un air froid en mouvement d'un air plus chaud qu'il soulève.
B.	est l'arrivée d'un air froid sur une surface polaire glacée.
C.	est l'arrivée d'un air froid et lourd qui stabilise la basse couche atmosphérique.
D.	est généralement associé à des brises marines d'ouest.

1.12	Les courants de vent puissants que l'on rencontre à très haute altitude sont nommés:
A.	jet-stream.
B.	jet-lag.
C.	tornado.
D.	Rafale.

1.13	La couche de l'atmosphère où se concentrent les phénomènes météorologiques est la :
A.	stratosphère.
B.	troposphère.
C.	mésosphère.
D.	thermosphère.

1.14	Le principal danger induit par le brouillard sur le vol est :
A.	la formation de givrage possible en toutes saisons.
B.	la turbulence associée.
C.	la diminution de la visibilité.
D.	le risque de foudroiement.

1.15	Dans l'atmosphère standard, la température au niveau de la mer est de :
A.	0 °C.
B.	10 °C.
C.	15 °C.
D.	20 °C.

1.16	À 4 000 m, le capteur du ballon sonde relève une température de -1°C. Nous en concluons que l'atmosphère à 4 000 m est :
A.	plus froide que l'atmosphère standard.
B.	conforme à l'atmosphère standard.
C.	plus chaude que l'atmosphère standard.
D.	plus riche en dioxygène qu'au niveau du sol.
 


1.17	La brise de pente (montante) se forme en région :
A montagneuse et de nuit.
B. côtière et de nuit.
C. montagneuse et de jour.
D. côtière et de jour.

1.18	Je monte dans l'avion au matin. L'altimètre réglé sur le QNH hier soir indique une altitude supérieure à celle de l'aérodrome.
A La pression sur l'aérodrome a baissé pendant la nuit.
B. La température a baissé sur l'aérodrome pendant la nuit.
C. La pression sur l'aérodrome a augmenté pendant la nuit.
D. L'altimètre est forcément devenu défectueux.

1.19	Un vent du 090/20 vient :
A de l'ouest à une vitesse de 20 kt.
B. de l'est à une vitesse de 20 kt.
C. de l'est à une vitesse de 20 km/h-1.
D. de l'ouest à une vitesse de 20 km/h-1.


1.20	Sur des cartes TEMSI, on peut lire une validité au 14/10/2019 15 UTC. Sachant que le 14 octobre 2019, la France était en « heure d'été », à quelle heure légale correspond cette prévision?
A 13 h.
B. 14 h.
C. 16 h.
D. 17 h.




















Carte TEMSI
 

2.1	Pour un aéronef en vol en palier stabilisé (vol horizontal stabilisé), quelle proposition est correcte?
A.	La portance est légèrement inférieure au poids.
B.	La portance équilibre la traînée.
C.	La portance et la traction sont identiques.
D.	La portance équilibre le poids.

2.2	Les dispositifs hypersustentateurs ont pour but :
A.	de diminuer la portance à vitesse élevée (par exemple : pour une descente d'urgence).
B.	d'augmenter la vitesse de décrochage pour certaines manœuvres.
C.	de diminuer la traînée pour certaines manœuvres.
D.	de diminuer la vitesse de décrochage dans certaines phases de vol (par exemple: au décollage et à l'atterrissage).

2.3	Le facteur de charge subi par un aéronef en virage en palier :
A.	diminue avec l'inclinaison.
B.	est toujours égal à 2.
C.	ne dépend que du type d'aéronef.
D.	augmente avec l'inclinaison.

2.4	Le profil d'une aile est lisse lorsque :
A.	les becs de bord d'attaque et les volets sont rentrés.
B.	les becs de bord d'attaque sont rentrés et les volets sont sortis.
C.	les becs de bord d'attaque sont sortis et les volets sont rentrés.
D.	les becs de bord d'attaque et les volets sont sortis.

2.5	Pour calculer la distance de décollage d'un avion, il faut prendre en compte :
A.	la masse de l'avion uniquement.
B.	la température, l'altitude de l'aéroport, la masse de l'avion.
C.	l'altitude de l'aéroport uniquement.
D.	aucun de ces éléments.

2.6	La traînée induite est une conséquence de:
A.	l'interaction du fuselage et de l'aile.
B.	la rotation de l'hélice.
C.	la différente de pression entre l'intrados et l'extrados.
D.	l'usage d'un train fixe.
 


2.7	L'incidence d'une aile est positive lorsque:
A l'écoulement est parallèle à la corde du profil.
B. l'écoulement attaque le profil du côté de l'extrados.
C. l'écoulement attaque le profil du côté de l'intrados.
D. l'aéronef est en vol dos stabilisé.

2.8	Lors d'une ressource, le facteur de charge:
A augmente.
B. diminue et la vitesse de décrochage augmente.
C. reste constant.
D. diminue ainsi que la vitesse de décrochage.

2.9	Ce qui assure la plus grande stabilité d'un aéronef est :
A le dièdre et la flèche positifs.
B. le dièdre négatif et la flèche nulle.
C. le dièdre et la flèche négatifs.
D. le dièdre positif et la flèche nulle.

2.10	L'angle d'incidence d'un profil est l'angle formé entre :
A la corde du profil et l'horizontale.
B. l'axe longitudinal de l'avion et la direction du vent relatif.
C. la direction du vent relatif et l'horizontale.
D. la corde du profil et la direction du vent relatif.

2.11	Lorsqu'un aéronef est centré avant:
A sa stabilité augmente.
B. sa maniabilité augmente.
C. sa maniabilité et sa stabilité ne sont pas modifiées.
D. sa stabilité diminue.

2.12	L'assistance gravitationnelle :
A permet le retour du lanceur sur Terre.
B. est une ligne téléphonique entre l'ISS et la Terre en cas de besoin d'assistance.
C. est utilisée comme « moteur » afin d'accélérer les sondes lors de leurs voyages interstellaires.
D. est un propulseur.

2.13	La corde de profil de l'aile est le segment qui joint : A l'emplanture à l'extrémité de l'aile.
B. les deux extrémités de l'aile.
C. le bord d'attaque au bord de fuite.
D. la partie la plus large entre l'intrados et l'extrados.
 

2.14	L'origine de la sustentation de l'aile résulte de l'apparition :
A.	d'une dépression à l'extrados et à l'intrados.
B.	d'une surpression à l'intrados et à l'extrados.
C.	d'une dépression à l'extrados et d'une surpression à l'intrados.
D.	d'une surpression à l'extrados et d'une dépression à l'intrados.

2.15	L'angle de pente est :
A.	l'angle entre l'horizontale et l'axe longitudinal de l'avion.
B.	l'angle entre la corde de profil de l'aile et le vent relatif.
C.	l'angle affiché sur l'horizon artificiel du pilote.
D.	l'angle entre l'horizontale et la trajectoire réelle de l'avion.

2.16	En vol, si le pilote tire fortement sur le manche, le facteur de charge :
A.	augmente.
B.	diminue.
C.	reste constant.
D.	devient nul.
2.17	Parmi les éléments suivants, celui qui a une influence sur la position du centre de gravité est:
A.	la trajectoire (palier, montée, descente).
B.	la vitesse.
C.	le niveau de carburant dans les réservoirs.
D.	l'inclinaison.

2.18	En soufflerie, si on multiplie par 3 la vitesse du vent relatif, la valeur de la portance est :
A.	multipliée par 3.
B.	multipliée par 9.
C.	multipliée par 6.
D.	multipliée par 12.

2.19	Le réglage de l'hélice en plein petit pas au décollage a pour but de :
A.	diminuer la distance de décollage et la pente de montée.
B.	augmenter la distance de décollage et diminuer la pente de montée.
C.	diminuer la distance de décollage et augmenter la pente de montée.
D.	augmenter la distance de décollage et la pente de montée.

2.20	Pour un aéronef en montée rectiligne uniforme, la force de traction de l'hélice est fonction :
A.	uniquement de la traînée.
B.	de la traînée, du poids et de l'angle de montée.
C.	uniquement du poids et de la portance.
D.	du poids et de l'angle de montée.
 

3.1	Parmi ces instruments, celui qui utilise un gyroscope est :
A.	l'horizon artificiel.
B.	le compas magnétique.
C.	l'anémomètre.
D.	le tachymètre.

3.2	Quels sont les éléments présents dans une commande de vol mécanique simple d'un avion d'aéroclub ?
A.	Câbles et poulies.
B.	Tuyaux hydrauliques et serve-commande.
C.	Moteurs électriques et câbles.
D.	Bielles et pistons.

3.3	Dans un moteur à 4 temps, la compression intervient après :
A.	la combustion.
B.	la détente.
C.	l'admission.
D.	l'échappement.

3.4	Sur un parapente, la liaison entre les élévateurs et l'aile est assurée par :
A.	des ficelles.
B.	des cordelettes.
C.	des lignes.
D.	des suspentes.

3.5	Pour indiquer l'altitude, l'altimètre utilise :
A.	la différence entre la pression totale et la pression dynamique.
B.	la pression totale.
C.	la pression dynamique.
D.	la pression statique.

3.6	Les cadres :
A.	ont dans le fuselage le même rôle que les nervures dans les ailes.
B.	sont situés en bout d'aile pour éviter les tourbillons marginaux.
C.	sont les pièces maîtresses du fuselage qui supportent les efforts de flexion.
D.	sont toujours montés par paire pour augmenter leur solidité.
 


3.7	En aéromodélisme, un avion d'apprentissage« deux axes» est pilotable sur les axes de:
A.	roulis et lacet.
8. roulis uniquement.
C. tangage et roulis.
O. tangage et lacet.

3.8	Durant un cycle de fonctionnement d'un moteur à pistons (4 temps), le seul temps où le piston monte du point mort bas au point mort haut avec les soupapes fermées est le temps:
A. d'admission.
8. de compression.
C. de combustion-détente.
O. d'échappement.

3.9	L'avion représenté sur la photographie ci-après possède un train :
A. classique.
8. tricycle.
C. caréné.
O. rentrant.









3.10	En considérant la figure ci-dessous, les combinaisons correctes sont :
A. A2, 84, C3, 01.
8. A2, 84, C1, 03.
C. A4, 85, C2, 01.
O. A4, 82, C3, 05.	A : Bord d;attaque	3
B : Bord de fuite
C : Saumon d'aile D: Extrados
 


3.11	Sur le plan ci-dessous, la combinaison correcte est : A 1 : aileron, 2 : saumon, 3 : volet, 4 : gouverne de profondeur.
B. 1 : volet, 2 : saumon, 3 : aileron, 4 : gouverne de profondeur.
C. 1 : aileron, 2: saumon, 3 : volet, 4: gouverne de direction.
O. 1 : aileron, 2 : tab, 3 : volet, 4 : gouverne de direction.




 
	,I.	,,
 
-1	....
-.......,,....- :.::,:::J	2
\.
 
3







3.12	Sur un avion certifié, un moteur à pistons contenant 4 cylindres est pourvu au total de : A 2 bougies d'allumage.
B. 4 bougies d'allumage.
C. 8 bougies d'allumage.
O. 0 bougie d'allumage.

3.13	Cette machine est équipée :
A d'un train classique et d'ailes hautes.
B. d'un train tricycle et d'ailes hautes.
C. d'un train classique et d'ailes basses.
O. d'un train tricycle et d'ailes basses.

 


3.14	Quelle est la mauvaise classification?
A. Aérodynes non motorisés : deltaplanes, planeurs
B. Aérostat : deltaplane, ballons, dirigeables
C. Engins aérospatiaux : lanceurs, fusées
O. Engins spatiaux : satellites, sondes

3.15	L'élément fléché correspond à :
A. l'emplanture.
B. un aileron basse vitesse.
C. un volet.
O. un winglet.






3.16	Un empennage dit« canard » :
A. est situé à l'avant de l'avion.
B. remplace les ailerons.
C. est synonyme d'un empennage en V.
O. est situé à l'arrière de l'avion.

3.17	Les acteurs du transport aérien (motoristes, compagnies aériennes, pétroliers) se sont engagés dans le développement d'un nouveau carburant pour remplacer à terme le kérosène (JET A1), compatible et mixable avec le kérosène. De quel carburant s'agit-il ?
A. EFIS : Ecological Fuel International Standard
B. JET A2 : 2ème génération du JET
C. AKI : Alternative Kerosene Initiative
O. SAF : Sustainable Aviation Fuel

3.18	Pour effectuer une rotation autour de l'axe de roulis, le pilote doit :
A. modifier la profondeur à l'aide du compensateur.
B. déplacer le manche en avant ou en arrière.
C. déplacer le manche à gauche ou à droite.
O. actionner le palonnier.
 


3.19	Le rotor anticouple d'un hélicoptère permet de contrôler :
A.	la rotation autour de l'axe de tangage.
B.	la rotation autour de l'axe de lacet.
C.	la rotation autour de l'axe de roulis.
D.	la vitesse ascensionnelle.

3.20	Le variomètre indique :
A.	la vitesse horizontale.
B.	la vitesse verticale.
C.	l'altitude.
D.	les variations de régime moteur.
 


4.1	Sachant que votre route magnétique est de 090° et que vous êtes en VFR, quel niveau de vol (Flight Level) choisissez-vous pour respecter la règle de la semi-circulaire ?
A.	60.
B.	65.
C.	70.
D.	75.

4.2	Lorsque vous vous trouvez au point d'attente, vous effectuez le contrôle des magnétos. Cela consiste à contrôler te bon fonctionnement :
A.	des deux systèmes d'allumage du moteur.
B.	du compas et du cap magnétique.
C.	du gyroscope du conservateur de cap.
D.	du gyroscope de l'horizon artificiel.

4.3	Pour voler en France, les avions certifiés doivent obligatoirement posséder :
A.	la licence de station d'aéronefs (LSA).
B.	l'habilitation de radiotéléphonie en langue française.
C.	la facture d'achat de l'avion.
D.	les certificats de navigabilité (CEN) et d'examen de navigabilité (CON).

4.4	Votre vol VFR vous amène à traverser une TMA de classe D :
A.	c'est une zone non contrôlée.
B.	c'est une zone contrôlée qui nécessite une clairance.
C.	c'est une zone contrôlée qui ne nécessite jamais de clairance.
D.	c'est une zone interdite au vol VFR.

4.5	Un aérodrome ouvert à ta CAP :
A.	n'est ouvert qu'aux appareils d'État.
B.	est ouvert à la circulation aérienne publique.
C.	est interdit aux ULM.
D.	nécessite un certificat d'aptitude à se poser.

4.6	La cause d'accident ta moins fréquente en aéronautique est :
A.	le pilote.
B.	la météo.
C.	les infrastructures.
D.	l'aéronef.
 


4.7	Pour afficher leur altitude par rapport au niveau moyen de la mer, les pilotes doivent afficher sur leur altimètre un calage :
A.	QNH.
B.	QFE.
C.	QFU.
D.	1013.0.

4.8	Un tour de piste main gauche signifie :
A.	que l'avion doit se poser sur la partie gauche de la piste.
B.	que le pilote doit piloter avec la main gauche pour des raisons de sécurité.
C.	que le pilote effectue le dernier virage avec la piste à sa gauche.
D.	que la manche à air est à gauche de la piste.

4.9	Comment est appelé l'angle entre le nord vrai et le nord magnétique ?
A.	déviation.
B.	déclinaison magnétique.
C.	erreur de parallaxe.
D.	inclinaison magnétique.

4.10	La route géographique ou route vraie sur la première branche est de 330°, la déclinaison magnétique est de 2°E, votre route magnétique est de :
A.	328°.
B.	330°.
C.	332°.
D.	32°.

4.11	À la radio, le signal de détresse est :
A.	« Mayday ».
B.	« Mayday, Mayday, Mayday ».
C.	« Panne, Panne, Panne ».
D.	« Panne ».

4.12	En France métropolitaine, en un lieu déterminé, la nuit aéronautique commence :
A.	30 minutes après le coucher du soleil et se termine 30 minutes avant le lever du soleil.
B.	30 minutes après le coucher du soleil et se termine 30 minutes après le lever du soleil.
C.	30 minutes avant le coucher du soleil et se termine 30 minutes après le lever du soleil.
D.	30 minutes avant le coucher du soleil et se termine 30 minutes avant le lever du soleil.
 

4.13	Compte tenu des règles de priorité, quelle manœuvre doit réaliser chaque pilote se faisant face pour éviter un accident ?
A.	Les deux tournent à gauche.
B.	Chacun vire à droite.
C.	1 tourne à gauche et 2 tourne à droite.
D.	1 tourne à droite et 2 tourne à gauche.

4.14	Sur tous les aérodromes ouverts à la circulation aérienne publique (CAP), la réglementation impose la présence :
A.	du numéro de la piste en service sur la tour de contrôle.
B.	d'un hangar pour héberger les avions de passage.
C.	d'une manche à air.
D.	d'un T indiquant la piste en service.

4.15	Un avion de ligne effectue la liaison New York - Paris à la vitesse propre de 900 km/h. Il évolue dans un Jet Stream de 300 km/h orienté d'ouest en est. Quelle est alors sa vitesse sol ?
A.	1200 km/h.
B.	900 km/h.
C.	600 km/h.
D.	300 km/h.

4.16	En vol, si la météo devait se dégrader fortement devant vous, votre instructeur pourrait vous conseiller de :
A.	faire demi-tour.
B.	maintenir votre trajectoire en espérant que cette dégradation n'est que passagère.
C.	descendre rapidement près du sol pour mieux voir.
D.	maintenir votre trajectoire en découvrant les bases du vol aux instruments.

4.17	La fréquence radio de détresse est:
A.	le 121,5 MHz.
B.	le 122,5 MHz.
C.	le 123,5 MHz.
D.	le 130 MHz.

4.18	Au bout de 10 minutes de vol, vous ressentez des nausées, votre instructeur vous tend un sac à vomi que vous ne tardez pas à utiliser ... Vous êtes victime :
A.	d'un conflit vestibule-visuel.
B.	d'une otite barotraumatique.
C.	d'une hypoxie.
D.	d'une embolie pulmonaire.
 

4.19	La responsabilité de l'entretien d'un ULM est réglementairement assurée par :
A.	le propriétaire.
B.	un organisme agréé.
C.	le constructeur.
D.	le mécanicien du club.

4.20	La visite prévol est effectuée :
A.	une fois par jour par le commandant de bord.
B.	systématiquement par le commandant de bord avant chaque vol.
C.	une fois par jour par le chef mécanicien.
D.	après chaque réparation.
 

5.1	Un as de la Première Guerre mondiale a laissé son nom à une manœuvre acrobatique destinée à inverser rapidement la direction du vol. Il s'agit de :
A.	René Fonck.
B.	Georges Guynemer.
C.	Charles Nungesser.
D.	Max Immelmann.

5.2	La compagnie Air France a été créée en :
A.	1933.
B.	1945.
C.	1920.
D.	1970.

5.3	On attribue aux Chinois l'invention d'un engin volant "plus lourd que l'air" qui est :
A.	la lanterne céleste.
B.	le cerf-volant.
C.	le ballon dirigeable.
D.	le ballon à gaz.

5.4	En 1910, Henri Fabre est le premier à décoller à bord d'un :
A.	bimoteur.
B.	hydravion.
C.	planeur.
D.	autogire.

5.5	Léonard de Vinci a envisagé un modèle de parachute :
A.	composé d'une voilure tournante en plumes d'oiseau.
B.	en forme de « tente » à faces rectangulaires ou triangulaires.
C.	comportant quatre vis d'Archimède.
D.	de forme hémisphérique.

5.6	Le tigre est un hélicoptère :
A.	américain, complémentaire de !'Apache.
B.	soviétique, symbole de la Guerre froide.
C.	européen, de transport de troupes.
D.	franco-allemand, capable d'effectuer un looping

5.7	En quelle année a été créée la première patrouille de France?
A.	1946.
B.	1953.
C.	1920.
D.	1961
 


5.8	Wernher Von Braun est le père du programme spatial américain ayant amené un homme sur la
Lune, il est également à l'origine de :
A. l'avion Messerschmitt 262.
B. l'arme de représailles V2.
C. l'avion fusée Me163.
O. le lanceur Soyouz.

5.9	En 2009, Airbus inaugure le premier vol commercial du plus grand avion civil au monde. Cet avion s'appelle:
A. A400M.
B. A380.
C. Triple 7.
O. BELUGA.

5.10	Dans quelle ville se trouve la base aérienne de la patrouille de France ?
A. Salon-de-Provence.
B. Istres.
C. Étampes.
O. Le Bourget.

5.11	L'avion ci-dessous est de conception des années :
A. 1950.
B. 1980.
C. 1670.
O. 2000.



5.12	Au cours de la Première Guerre mondiale, la vitesse moyenne des avions de chasse sera multipliée par :
A. 2.
B. 4.
C. 6.
O. 8.

5.13	Le premier vol de l'Airbus A380 a eu lieu en :
A. 2005.
B. 2000.
C. 2010.
O. 1995.
 

5.14	Un peu avant la Première Guerre mondiale, l'ingénieur Raoul Badin se rend célèbre par une innovation concernant :
A.	un instrument de bord destiné à mesurer la vitesse de l'aéronef par rapport à l'air dans lequel il évolue.
B.	le tir à travers l'hélice sans heurter les pales.
C.	la disposition en étoile des cylindres d'un moteur.
D.	le siège éjectable.

5.15	Les premières compétitions aériennes avant la Première Guerre mondiale ont été soutenues par de grands donateurs comme :
A.	Michelin.
B.	Dassault.
C.	Chanel.
D.	Lacoste.

5.16	En 1921, Adrienne Bolland fut la première aviatrice à traverser :
A.	la cordillère des Andes.
B.	les Alpes.
C.	la Méditerranée entre le continent et la Corse.
D.	le continent antarctique.

5.17	En quelle année Charles Lindbergh a-t-il traversé l'Atlantique pour la première fois?
A.	1909.
B.	1913.
C.	1927.
D.	1941.

5.18	En 1930, les pilotes français Costes et Bellonte traversent l'Atlantique Nord dans le sens Paris New York aux commandes du:

A.	Breguet 19 « Point d'interrogation ».
B.	Bernard 191 GR « Oiseau Canari ».
C.	Ryan NYP « Spirit of St-Louis ».
D.	Latécoère 28-3 « Comte de la Vaulx ».

5.19	Parmi ces avions à réacteurs, celui ayant initié le transport de masse en nombre de passagers est:
A.	le Boeing 8747.
B.	le Concorde.
C.	l'Airbus Beluga.
D.	l'Airbus A380.
 

5.20	Le premier vol commercial d'Ariane 6 a eu lieu en :
A 2025.
B.	2020.
C.	2018.
D.	2010.

    """  # Texte vide pour le test, peut être remplacé par du texte réel ou un fichier
    # Pour un fichier Word
    #questions = parse_qcm_from_word(r"doc\Examen BIA2025 Europe.docx")
    # Exemple d'utilisation simple
    if document_text.strip():
        questions = parse_qcm_text(document_text)
        
        # Affichage des résultats
        print(f"Nombre de questions trouvées : {len(questions)}")
        
        for i, question in enumerate(questions[:3], 1):  # Affiche les 3 premières questions
            print(f"\n--- Question {i} ---")
            print(f"Question: {question[0]}")
            print(f"A) {question[1]}")
            print(f"B) {question[2]}")
            print(f"C) {question[3]}")
            print(f"D) {question[4]}")
            print(f"Réponse: {question[5] if question[5] else 'À déterminer'}")
        
        # Sauvegarde
        save_to_csv(questions)