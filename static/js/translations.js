/**
 * Sign labels in English, Hindi (Devanagari), and Marathi for A–Z and 0–9.
 * Used for display and TTS language.
 */
const SIGN_TRANSLATIONS = {
  en: {
    A: "A", B: "B", C: "C", D: "D", E: "E", F: "F", G: "G", H: "H", I: "I",
    J: "J", K: "K", L: "L", M: "M", N: "N", O: "O", P: "P", Q: "Q", R: "R",
    S: "S", T: "T", U: "U", V: "V", W: "W", X: "X", Y: "Y", Z: "Z",
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    Hi: "Hi", Hello: "Hello", Bye: "Bye", ThankYou: "Thank you", Welcome: "Welcome",
    Yes: "Yes", No: "No", Please: "Please", Sorry: "Sorry", Help: "Help",
    Good: "Good", Morning: "Morning", Night: "Night", Love: "Love", Water: "Water", Food: "Food",
    Name: "Name", What: "What", Where: "Where", When: "When", Why: "Why", How: "How",
    You: "You", We: "We", They: "They", Me: "Me", My: "My", Your: "Your",
    Friend: "Friend", Family: "Family", Home: "Home", School: "School", Work: "Work",
    Come: "Come", Go: "Go", Stop: "Stop", Wait: "Wait", Again: "Again", Slow: "Slow",
    Understand: "Understand", DontUnderstand: "Don't understand", Deaf: "Deaf", Hearing: "Hearing"
  },
  hi: {
    A: "ए", B: "बी", C: "सी", D: "डी", E: "ई", F: "एफ", G: "जी", H: "एच", I: "आई",
    J: "जे", K: "के", L: "एल", M: "एम", N: "एन", O: "ओ", P: "पी", Q: "क्यू", R: "आर",
    S: "एस", T: "टी", U: "यू", V: "वी", W: "डब्ल्यू", X: "एक्स", Y: "वाई", Z: "जेड",
    "0": "शून्य", "1": "एक", "2": "दो", "3": "तीन", "4": "चार",
    "5": "पाँच", "6": "छह", "7": "सात", "8": "आठ", "9": "नौ",
    Hi: "नमस्ते", Hello: "हैलो", Bye: "अलविदा", ThankYou: "धन्यवाद", Welcome: "स्वागत",
    Yes: "हाँ", No: "नहीं", Please: "कृपया", Sorry: "क्षमा", Help: "मदद",
    Good: "अच्छा", Morning: "सुप्रभात", Night: "रात", Love: "प्यार", Water: "पानी", Food: "भोजन",
    Name: "नाम", What: "क्या", Where: "कहाँ", When: "कब", Why: "क्यों", How: "कैसे",
    You: "आप", We: "हम", They: "वे", Me: "मैं", My: "मेरा", Your: "आपका",
    Friend: "दोस्त", Family: "परिवार", Home: "घर", School: "स्कूल", Work: "काम",
    Come: "आओ", Go: "जाओ", Stop: "रुको", Wait: "इंतज़ार", Again: "फिर", Slow: "धीरे",
    Understand: "समझ", DontUnderstand: "नहीं समझ", Deaf: "बधिर", Hearing: "सुनने वाला"
  },
  mr: {
    A: "ए", B: "बी", C: "सी", D: "डी", E: "ई", F: "एफ", G: "जी", H: "एच", I: "आय",
    J: "जे", K: "के", L: "एल", M: "एम", N: "एन", O: "ओ", P: "पी", Q: "क्यू", R: "आर",
    S: "एस", T: "टी", U: "यू", V: "वी", W: "डब्ल्यू", X: "एक्स", Y: "वाय", Z: "झेड",
    "0": "शून्य", "1": "एक", "2": "दोन", "3": "तीन", "4": "चार",
    "5": "पाच", "6": "सहा", "7": "सात", "8": "आठ", "9": "नऊ",
    Hi: "नमस्कार", Hello: "हॅलो", Bye: "गुडबाय", ThankYou: "धन्यवाद", Welcome: "स्वागत",
    Yes: "होय", No: "नाही", Please: "कृपया", Sorry: "माफ करा", Help: "मदत",
    Good: "चांगले", Morning: "सकाळ", Night: "रात्र", Love: "प्रेम", Water: "पाणी", Food: "अन्न",
    Name: "नाव", What: "काय", Where: "कुठे", When: "केव्हा", Why: "का", How: "कसे",
    You: "तू", We: "आम्ही", They: "ते", Me: "मी", My: "माझे", Your: "तुझे",
    Friend: "मित्र", Family: "कुटुंब", Home: "घर", School: "शाळा", Work: "काम",
    Come: "ये", Go: "जा", Stop: "थांब", Wait: "वाट", Again: "पुन्हा", Slow: "हळू",
    Understand: "समज", DontUnderstand: "समजत नाही", Deaf: "बधिर", Hearing: "ऐकणारा"
  }
};

/** TTS language codes for Web Speech API */
const TTS_LANG = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

function getDisplaySign(sign, langCode) {
  if (sign === undefined || sign === null) return "—";
  if (typeof sign === "number" && sign >= 0 && sign <= 9) sign = String(sign);
  sign = String(sign);
  const lang = SIGN_TRANSLATIONS[langCode] || SIGN_TRANSLATIONS.en;
  return lang[sign] != null ? lang[sign] : sign;
}

function getTTSLang(langCode) {
  return TTS_LANG[langCode] || "en-IN";
}
