import csv
import random
from io import StringIO


def get_nina_policy(small=False):
    mapping_ARS_bundesland = {
        '01': 'Schleswig-Holstein',
        '02': 'Hamburg',
        '03': 'Niedersachsen',
        '04': 'Bremen',
        '05': 'Nordrhein-Westfalen',
        '06': 'Hessen',
        '07': 'Rheinland-Pfalz',
        '08': 'Baden-Württemberg',
        '09': 'Bayern',
        '10': 'Saarland',
        '11': 'Berlin',
        '12': 'Brandenburg',
        '13': 'Mecklenburg-Vorpommern',
        '14': 'Sachsen',
        '15': 'Sachsen-Anhalt',
        '16': 'Thüringen',
    }

    ARS = csv.reader(StringIO(get_ars()), delimiter=',')

    ARS_by_bundesland = {k: [] for k in mapping_ARS_bundesland.values()}
    for row in ARS:
        ARS_by_bundesland[mapping_ARS_bundesland[row[0][0:2]]].append(row)

    if small:
        ARS_by_bundesland = {bl: ARS_by_bundesland[bl] for bl in random.choices(list(ARS_by_bundesland.keys()), k=1)}
        ARS_by_bundesland = {bl: random.choices(ARS_by_bundesland[bl],
                                                k=min(len(ARS_by_bundesland[bl]), 1))
                             for bl in list(ARS_by_bundesland.keys())}

    rooms = {'nina_warnungen':
                 {'alias': 'nina_warnungen',
                  'room_name': "NINA Warnungen",
                  'is_space': True,
                  }}

    for bundesland, kreisliste in ARS_by_bundesland.items():
        rooms[bundesland] = {"id": '',
                             "alias": bundesland,
                             "room_name": bundesland,
                             "is_space": True,
                             "parent_spaces": ['nina_warnungen']}
        for ars_code, name in kreisliste:
            rooms[name] = {"id": '',
                           "alias": name,
                           "room_name": name,
                           "parent_spaces": [bundesland],
                           'actions': [{
                               "template": "rss",
                               "format": {
                                   "link": f"https://warnung.bund.de/api31/mowas/rss/{ars_code}0000000.rss"},
                           }]}

    policy = {
        "schemaVersion": 1,
        "policy_key": f"nina{'_small' if small else ''}",
        "bot_actions": {
            "rss": {
                "bots": [
                    "@bot.rss:wurzelraum.org"
                ],
                "commands": [
                    "!rss subscribe {link}",
                    "!rss subscriptions"
                ],
            }},
        "rooms": rooms
    }
    return policy


def get_ars():
    return """01001,Flensburg Stadt
01002,Kiel Landeshauptstadt
01003,Lübeck Hansestadt
01004,Neumünster Stadt
01051,Dithmarschen
01053,Herzogtum Lauenburg
01054,Nordfriesland
01055,Ostholstein
01056,Pinneberg
01057,Plön
01058,Rendsburg-Eckernförde
01059,Schleswig-Flensburg
01060,Segeberg
01061,Steinburg
01062,Stormarn
02000,Hamburg Freie und Hansestadt
03101,Braunschweig Stadt
03102,Salzgitter Stadt
03103,Wolfsburg Stadt
03151,Gifhorn
03153,Goslar
03154,Helmstedt
03155,Northeim
03157,Peine
03158,Wolfenbüttel
03159,Göttingen
03241,Region Hannover
03251,Diepholz
03252,Hameln-Pyrmont
03254,Hildesheim
03255,Holzminden
03256,Nienburg (Weser)
03257,Schaumburg
03351,Celle
03352,Cuxhaven
03353,Harburg
03354,Lüchow-Dannenberg
03355,Lüneburg
03356,Osterholz
03357,Rotenburg (Wümme)
03358,Heidekreis
03359,Stade
03360,Uelzen
03361,Verden
03401,Delmenhorst Stadt
03402,Emden Stadt
03403,Oldenburg (Oldenburg) Stadt
03404,Osnabrück Stadt
03405,Wilhelmshaven Stadt
03451,Ammerland
03452,Aurich
03453,Cloppenburg
03454,Emsland
03455,Friesland
03456,Grafschaft Bentheim
03457,Leer
03458,Oldenburg
03459,Osnabrück
03460,Vechta
03461,Wesermarsch
03462,Wittmund
04011,Bremen Stadt
04012,Bremerhaven Stadt
05111,Düsseldorf Stadt
05112,Duisburg Stadt
05113,Essen Stadt
05114,Krefeld Stadt
05116,Mönchengladbach Stadt
05117,Mülheim an der Ruhr Stadt
05119,Oberhausen Stadt
05120,Remscheid Stadt
05122,Solingen Klingenstadt
05124,Wuppertal Stadt
05154,Kleve
05158,Mettmann
05162,Rhein-Kreis Neuss
05166,Viersen
05170,Wesel
05314,Bonn Stadt
05315,Köln Stadt
05316,Leverkusen Stadt
05334,Städteregion Aachen
05358,Düren
05362,Rhein-Erft-Kreis
05366,Euskirchen
05370,Heinsberg
05374,Oberbergischer Kreis
05378,Rheinisch-Bergischer Kreis
05382,Rhein-Sieg-Kreis
05512,Bottrop Stadt
05513,Gelsenkirchen Stadt
05515,Münster Stadt
05554,Borken
05558,Coesfeld
05562,Recklinghausen
05566,Steinfurt
05570,Warendorf
05711,Bielefeld Stadt
05754,Gütersloh
05758,Herford
05762,Höxter
05766,Lippe
05770,Minden-Lübbecke
05774,Paderborn
05911,Bochum Stadt
05913,Dortmund Stadt
05914,Hagen Stadt der FernUniversität
05915,Hamm Stadt
05916,Herne Stadt
05954,Ennepe-Ruhr-Kreis
05958,Hochsauerlandkreis
05962,Märkischer Kreis
05966,Olpe
05970,Siegen-Wittgenstein
05974,Soest
05978,Unna
06411,Darmstadt Wissenschaftsstadt
06412,Frankfurt am Main Stadt
06413,Offenbach am Main Stadt
06414,Wiesbaden Landeshauptstadt
06431,Bergstraße
06432,Darmstadt-Dieburg
06433,Groß-Gerau
06434,Hochtaunuskreis
06435,Main-Kinzig-Kreis
06436,Main-Taunus-Kreis
06437,Odenwaldkreis
06438,Offenbach
06439,Rheingau-Taunus-Kreis
06440,Wetteraukreis
06531,Gießen
06532,Lahn-Dill-Kreis
06533,Limburg-Weilburg
06534,Marburg-Biedenkopf
06535,Vogelsbergkreis
06611,Kassel documenta-Stadt
06631,Fulda
06632,Hersfeld-Rotenburg
06633,Kassel
06634,Schwalm-Eder-Kreis
06635,Waldeck-Frankenberg
06636,Werra-Meißner-Kreis
07111,Koblenz kreisfreie Stadt
07131,Ahrweiler
07132,Altenkirchen (Westerwald)
07133,Bad Kreuznach
07134,Birkenfeld
07135,Cochem-Zell
07137,Mayen-Koblenz
07138,Neuwied
07140,Rhein-Hunsrück-Kreis
07141,Rhein-Lahn-Kreis
07143,Westerwaldkreis
07211,Trier kreisfreie Stadt
07231,Bernkastel-Wittlich
07232,Eifelkreis Bitburg-Prüm
07233,Vulkaneifel
07235,Trier-Saarburg
07311,Frankenthal (Pfalz) kreisfreie Stadt
07312,Kaiserslautern kreisfreie Stadt
07313,Landau in der Pfalz kreisfreie Stadt
07314,Ludwigshafen am Rhein kreisfreie Stadt
07315,Mainz kreisfreie Stadt
07316,Neustadt an der Weinstraße kreisfreie Stadt
07317,Pirmasens kreisfreie Stadt
07318,Speyer kreisfreie Stadt
07319,Worms kreisfreie Stadt
07320,Zweibrücken kreisfreie Stadt
07331,Alzey-Worms
07332,Bad Dürkheim
07333,Donnersbergkreis
07334,Germersheim
07335,Kaiserslautern
07336,Kusel
07337,Südliche Weinstraße
07338,Rhein-Pfalz-Kreis
07339,Mainz-Bingen
07340,Südwestpfalz
08111,Stuttgart Stadtkreis
08115,Böblingen
08116,Esslingen
08117,Göppingen
08118,Ludwigsburg
08119,Rems-Murr-Kreis
08121,Heilbronn Stadtkreis
08125,Heilbronn
08126,Hohenlohekreis
08127,Schwäbisch Hall
08128,Main-Tauber-Kreis
08135,Heidenheim
08136,Ostalbkreis
08211,Baden-Baden Stadtkreis
08212,Karlsruhe Stadtkreis
08215,Karlsruhe
08216,Rastatt
08221,Heidelberg Stadtkreis
08222,Mannheim Stadtkreis
08225,Neckar-Odenwald-Kreis
08226,Rhein-Neckar-Kreis
08231,Pforzheim Stadtkreis
08235,Calw
08236,Enzkreis
08237,Freudenstadt
08311,Freiburg im Breisgau Stadtkreis
08315,Breisgau-Hochschwarzwald
08316,Emmendingen
08317,Ortenaukreis
08325,Rottweil
08326,Schwarzwald-Baar-Kreis
08327,Tuttlingen
08335,Konstanz
08336,Lörrach
08337,Waldshut
08415,Reutlingen
08416,Tübingen
08417,Zollernalbkreis
08421,Ulm Stadtkreis
08425,Alb-Donau-Kreis
08426,Biberach
08435,Bodenseekreis
08436,Ravensburg
08437,Sigmaringen
09161,Ingolstadt
09162,München Landeshauptstadt
09163,Rosenheim
09171,Altötting
09172,Berchtesgadener Land
09173,Bad Tölz-Wolfratshausen
09174,Dachau
09175,Ebersberg
09176,Eichstätt
09177,Erding
09178,Freising
09179,Fürstenfeldbruck
09180,Garmisch-Partenkirchen
09181,Landsberg am Lech
09182,Miesbach
09183,Mühldorf a.Inn
09184,München
09185,Neuburg-Schrobenhausen
09186,Pfaffenhofen a.d.Ilm
09187,Rosenheim
09188,Starnberg
09189,Traunstein
09190,Weilheim-Schongau
09261,Landshut
09262,Passau
09263,Straubing
09271,Deggendorf
09272,Freyung-Grafenau
09273,Kelheim
09274,Landshut
09275,Passau
09276,Regen
09277,Rottal-Inn
09278,Straubing-Bogen
09279,Dingolfing-Landau
09361,Amberg
09362,Regensburg
09363,Weiden i.d.OPf.
09371,Amberg-Sulzbach
09372,Cham
09373,Neumarkt i.d.OPf.
09374,Neustadt a.d.Waldnaab
09375,Regensburg
09376,Schwandorf
09377,Tirschenreuth
09461,Bamberg
09462,Bayreuth
09463,Coburg
09464,Hof
09471,Bamberg
09472,Bayreuth
09473,Coburg
09474,Forchheim
09475,Hof
09476,Kronach
09477,Kulmbach
09478,Lichtenfels
09479,Wunsiedel i.Fichtelgebirge
09561,Ansbach
09562,Erlangen
09563,Fürth
09564,Nürnberg
09565,Schwabach
09571,Ansbach
09572,Erlangen-Höchstadt
09573,Fürth
09574,Nürnberger Land
09575,Neustadt a.d.Aisch-Bad Windsheim
09576,Roth
09577,Weißenburg-Gunzenhausen
09661,Aschaffenburg
09662,Schweinfurt
09663,Würzburg
09671,Aschaffenburg
09672,Bad Kissingen
09673,Rhön-Grabfeld
09674,Haßberge
09675,Kitzingen
09676,Miltenberg
09677,Main-Spessart
09678,Schweinfurt
09679,Würzburg
09761,Augsburg
09762,Kaufbeuren
09763,Kempten (Allgäu)
09764,Memmingen
09771,Aichach-Friedberg
09772,Augsburg
09773,Dillingen a.d.Donau
09774,Günzburg
09775,Neu-Ulm
09776,Lindau (Bodensee)
09777,Ostallgäu
09778,Unterallgäu
09779,Donau-Ries
09780,Oberallgäu
10041,Regionalverband Saarbrücken
10042,Merzig-Wadern
10043,Neunkirchen
10044,Saarlouis
10045,Saarpfalz-Kreis
10046,St. Wendel
11000,Berlin Stadt
12051,Brandenburg an der Havel Stadt
12052,Cottbus Stadt
12053,Frankfurt (Oder) Stadt
12054,Potsdam Stadt
12060,Barnim
12061,Dahme-Spreewald
12062,Elbe-Elster
12063,Havelland
12064,Märkisch-Oderland
12065,Oberhavel
12066,Oberspreewald-Lausitz
12067,Oder-Spree
12068,Ostprignitz-Ruppin
12069,Potsdam-Mittelmark
12070,Prignitz
12071,Spree-Neiße
12072,Teltow-Fläming
12073,Uckermark
13003,Rostock
13004,Schwerin
13071,Mecklenburgische Seenplatte
13072,Landkreis Rostock
13073,Vorpommern-Rügen
13074,Nordwestmecklenburg
13075,Vorpommern-Greifswald
13076,Ludwigslust-Parchim
14511,Chemnitz Stadt
14521,Erzgebirgskreis
14522,Mittelsachsen
14523,Vogtlandkreis
14524,Zwickau
14612,Dresden Stadt
14625,Bautzen
14626,Görlitz
14627,Meißen
14628,Sächsische Schweiz-Osterzgebirge
14713,Leipzig Stadt
14729,Leipzig
14730,Nordsachsen
15001,Dessau-Roßlau Stadt
15002,Halle (Saale) Stadt
15003,Magdeburg Landeshauptstadt
15081,Altmarkkreis Salzwedel
15082,Anhalt-Bitterfeld
15083,Börde
15084,Burgenlandkreis
15085,Harz
15086,Jerichower Land
15087,Mansfeld-Südharz
15088,Saalekreis
15089,Salzlandkreis
15090,Stendal
15091,Wittenberg
16051,Erfurt Stadt
16052,Gera Stadt
16053,Jena Stadt
16054,Suhl Stadt
16055,Weimar Stadt
16061,Eichsfeld
16062,Nordhausen
16063,Wartburgkreis
16064,Unstrut-Hainich-Kreis
16065,Kyffhäuserkreis
16066,Schmalkalden-Meiningen
16067,Gotha
16068,Sömmerda
16069,Hildburghausen
16070,Ilm-Kreis
16071,Weimarer Land
16072,Sonneberg
16073,Saalfeld-Rudolstadt
16074,Saale-Holzland-Kreis
16075,Saale-Orla-Kreis
16076,Greiz
16077,Altenburger Land"""
