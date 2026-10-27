import random
import re

from app.integrations.base import ApiResult, LLMProvider, maybe_fail

HOOKS = {
    "en": [
        "Here's something most people never learn in school: {t}.",
        "Stop scrolling for a second, because {t} is wilder than it sounds.",
        "You've probably never thought about this, but {t}.",
        "Quick question. Did you know {t}?",
    ],
    "lv": [
        "Lūk, ko skolā parasti nemāca: {t}.",
        "Uz brītiņu apstājies, jo {t} ir daudz interesantāk, nekā izklausās.",
        "Tu droši vien par to nekad neesi domājis, bet {t}.",
    ],
}

BODY = {
    "en": [
        "Scientists have been looking into this for decades, and the answer keeps surprising them.",
        "It all comes down to how nature solves problems with the simplest tools it has.",
        "The more you dig into it, the stranger the details get.",
        "Some researchers call it one of the most underrated facts out there.",
        "And once you know it, you start noticing it everywhere.",
        "The short version is that evolution rarely does anything without a reason.",
        "What makes it even better is that it was discovered almost by accident.",
        "For a long time nobody believed it, until someone finally measured it properly.",
        "It sounds simple, but the numbers behind it are honestly hard to imagine.",
        "Most people get this completely wrong, and that's not really their fault.",
    ],
    "lv": [
        "Zinātnieki to pēta jau gadu desmitiem, un atbilde viņus joprojām pārsteidz.",
        "Viss ir saistīts ar to, kā daba atrisina problēmas ar visvienkāršākajiem līdzekļiem.",
        "Jo vairāk par to uzzini, jo dīvaināk tas šķiet.",
        "Daži pētnieki to sauc par vienu no visvairāk nenovērtētajiem faktiem.",
        "Un, kad to reiz uzzini, sāc to pamanīt visur.",
        "Interesantākais ir tas, ka tas tika atklāts gandrīz nejauši.",
        "Ilgu laiku tam neviens neticēja, līdz kāds to beidzot kārtīgi izmērīja.",
    ],
}

OUTROS = {
    "en": [
        "Follow for another fact tomorrow.",
        "Would you have guessed that? Let me know in the comments.",
        "Share this with someone who needs to know.",
    ],
    "lv": [
        "Seko, lai rīt uzzinātu vēl vienu faktu.",
        "Vai tu to zināji? Raksti komentāros.",
    ],
}

STOPWORDS = {"the", "a", "an", "of", "and", "why", "how", "what", "is", "are", "do", "does", "in", "on",
             "to", "can", "have", "has", "that", "for", "with", "you", "your", "each", "other", "than",
             "their", "they", "so", "far", "always", "never", "might", "will", "there", "be", "made",
             "kāpēc", "kā", "un", "ir", "par", "joprojām"}


class TemplateLLM(LLMProvider):
    name = "Veidņu ģenerators (mock)"

    def generate_script(self, prompt: str, topic: str, language: str) -> ApiResult:
        maybe_fail("openai")
        lang = language if language in HOOKS else "en"
        t = topic.rstrip(".?!")
        hook = random.choice(HOOKS[lang]).format(t=t[0].lower() + t[1:])

        # every now and then a too short script, so the retry path gets used
        if random.random() < 0.2:
            body = random.sample(BODY[lang], 1)
        else:
            body = random.sample(BODY[lang], random.randint(4, 5))
        text = " ".join([hook, *body, random.choice(OUTROS[lang])])

        words = [w for w in re.findall(r"[\wāčēģīķļņšūž]+", t.lower()) if w not in STOPWORDS and len(w) > 2]
        keywords = words[:3] or [t.lower()]
        data = {
            "script": text,
            "title": f"{t} #shorts",
            "description": f"{t}. {body[0]}\n\n#shorts #facts",
            "tags": list(dict.fromkeys(["shorts", "facts", *words[:5]])),
            "keywords": keywords,
            "fallback_keywords": ["nature", "abstract background", "city timelapse"],
        }
        tokens = len(prompt) // 4 + len(text) // 4
        return ApiResult(data, "openai", "chat.completions", units=tokens,
                         cost_eur=round(tokens * 0.0000012, 6), simulated=True)
