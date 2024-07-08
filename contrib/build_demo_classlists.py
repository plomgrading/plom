#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

"""Simple script to build a list of random first/last names.

The last names are currently hard-coded translations of the word "Extra", while the first-names are chosen to be common first names from each country.

Re-generation of data requires the names_dataset which is (essentially) a big dump of names from facebook, and also the alphabet-detector module.
"""

# some simple translations of extra into other languages courtesy of google-translate
# and https://www.indifferentlanguages.com/words/extra
extra_last_names = [
    "Extra",
    "Ekstra",
    "Supplémentaire",
    "Aukalega",
    "Aparteko",
    "Ychwanegol",
    "A-bharrachd",
    "Breise",
    "Papildomai",
    "Dodatkowy",
    "Okwengeziwe",
    "Tlaleletšo",
    "Ziada",
    "Ylimääräinen",
]


# some common M/F first names taken from the names_dataset - generated using the code below
# from alphabet_detector import AlphabetDetector
# from names_dataset import NameDataset
# import random
# ad = AlphabetDetector()
# extra_first_names = []
# nameset = NameDataset()
# # get 10 most common names from each country in database - but only Latin-script (sorry)
# for loc, name_data in nameset.get_top_names(20).items():
#     # name_data = {'M': list, 'F': list}
#     rc = random.choice(name_data["M"])
#     if ad.only_alphabet_chars(rc, "LATIN"):
#         extra_first_names.append(rc)
#     rc = random.choice(name_data["F"])
#     if ad.only_alphabet_chars(rc, "LATIN"):
#         extra_first_names.append(rc)
# print(sorted(list(set(extra_first_names))))


extra_first_names = [
    "Abdiel",
    "Adel",
    "Adi",
    "Adissa",
    "Adriana",
    "Agron",
    "Agus",
    "Akmal",
    "Alaa",
    "Alan",
    "Alejandra",
    "Alejandro",
    "Aleksandr",
    "Alemtsehay",
    "Ali",
    "Allen",
    "Amira",
    "Amr",
    "Anabela",
    "Andrey",
    "Anila",
    "Ariel",
    "Aya",
    "Aysel",
    "Ayu",
    "Ayşe",
    "Björn",
    "Carine",
    "Carla",
    "Carlos",
    "Chang",
    "Cheng",
    "Chiara",
    "Choukri",
    "Claudio",
    "Cristhian",
    "Devon",
    "Dimitra",
    "Elizabeth",
    "Fathmath",
    "Fatma",
    "Fernando",
    "Fiona",
    "Francis",
    "Frida",
    "Fábio",
    "Gelson",
    "Genesis",
    "Hanane",
    "Hawra",
    "Hernández",
    "Hiba",
    "Hilma",
    "Hüseyin",
    "Ifrah",
    "Ildikó",
    "Indah",
    "Inês",
    "Ivan",
    "Ivelina",
    "Javier",
    "Jemal",
    "Jenni",
    "Jesmond",
    "Jie",
    "Joana",
    "Joao",
    "Johan",
    "Jonas",
    "Josipa",
    "Juan",
    "Karel",
    "Kari",
    "Karin",
    "Katherine",
    "Khaled",
    "Kim",
    "Kitty",
    "Lavenia",
    "Laxmi",
    "Lebo",
    "Lebogang",
    "Lela",
    "Li",
    "Liline",
    "Linda",
    "Ling",
    "Luis",
    "Luka",
    "Maha",
    "Mahamadi",
    "Marcelina",
    "Marco",
    "Maria",
    "Markus",
    "Martha",
    "Marthese",
    "Marvín",
    "Mary",
    "Mary Grace",
    "María",
    "Masud",
    "Maxine",
    "Maya",
    "Małgorzata",
    "Mehdi",
    "Mekan",
    "Michalis",
    "Michel",
    "Miguel",
    "Mikael",
    "Milan",
    "Mohamed",
    "Mohammed",
    "Monika",
    "Monique",
    "Mouna",
    "Muhamad",
    "Muhammad",
    "Muhammed",
    "Munezero",
    "Nana",
    "Nargiza",
    "Neha",
    "Nicole",
    "Nikolay",
    "Nikos",
    "Nilsa",
    "Nishantha",
    "Niyonkuru",
    "Noel",
    "Noor",
    "Noriko",
    "Nur",
    "Or",
    "Peter",
    "Petra",
    "Philippe",
    "Rafał",
    "Raja",
    "Rajesh",
    "Ravi",
    "Renel",
    "Ricardo",
    "Richard",
    "Rodrigo",
    "Ryo",
    "Said",
    "Sam",
    "Sami",
    "Sanjida",
    "Sarah",
    "Shaik",
    "Sigríður",
    "Silvia",
    "Simona",
    "Siyabonga",
    "Snezana",
    "Solange",
    "Sophie",
    "Sri",
    "Steve",
    "Tamás",
    "Tanja",
    "Temo",
    "Thabang",
    "Thomas",
    "Trond",
    "Tural",
    "Valentina",
    "Valeria",
    "Vasile",
    "Victor",
    "Waisea",
    "Willem",
    "Yiota",
    "Yolani",
    "Yosiris",
    "Yves",
    "Zainab",
    "Zoila",
    "Špela",
]
