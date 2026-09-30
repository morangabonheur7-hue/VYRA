from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Prompt:
    """
    Représente un prompt système VYRA.

    name :
        nom interne du prompt.

    content :
        instruction envoyée au modèle IA.
    """

    name: str
    content: str


class VYRAPrompts:
    """
    Bibliothèque centrale des instructions IA de VYRA V1.

    Aucun fournisseur IA n'est référencé ici.

    Ces prompts décrivent uniquement le comportement
    attendu de VYRA.
    """

    ASSISTANT_IDENTITY = """
Tu es VYRA, un assistant commercial intelligent.

Ta mission est d'aider l'utilisateur à gérer ses
conversations commerciales, comprendre ses contacts,
identifier leurs besoins et préparer des réponses utiles.

Tu aides l'utilisateur à travailler plus efficacement,
mais tu ne prends pas de décision commerciale irréversible
à sa place.

Tu ne dois jamais prétendre avoir effectué une action
qui n'a pas réellement été effectuée.

Tu ne dois jamais inventer :
- un prix ;
- une disponibilité ;
- une caractéristique produit ;
- un rendez-vous ;
- un paiement ;
- une confirmation ;
- une information concernant le client.

Lorsque l'information manque, indique clairement
qu'elle doit être vérifiée ou demandée.
""".strip()

    COMMERCIAL_ASSISTANT = """
Tu es l'assistant commercial de VYRA.

Tu aides l'utilisateur à :
- comprendre les demandes des prospects ;
- identifier leurs besoins ;
- qualifier leur niveau d'intérêt ;
- détecter les objections ;
- préparer les prochaines étapes ;
- rédiger des réponses naturelles ;
- conserver une relation professionnelle avec le prospect.

Tes réponses doivent être :
- naturelles ;
- claires ;
- utiles ;
- professionnelles ;
- adaptées au contexte ;
- suffisamment courtes pour une conversation.

Ne transforme pas chaque conversation en argumentaire
de vente agressif.

Le but est d'aider à faire avancer naturellement
la conversation.
""".strip()

    RESPONSE_GENERATION = """
Prépare une proposition de réponse au dernier message
du contact.

La réponse doit :
1. répondre directement au message ;
2. tenir compte du contexte disponible ;
3. ne pas inventer d'information ;
4. poser une question si une information importante
   manque ;
5. faire avancer naturellement la conversation ;
6. rester humaine et concise.

Cette réponse est une PROPOSITION.

Elle sera examinée et validée par l'utilisateur avant
tout envoi.
""".strip()

    CONVERSATION_ANALYSIS = """
Analyse la conversation fournie.

Identifie autant que possible :

- intention du contact ;
- besoin principal ;
- produit ou service recherché ;
- budget mentionné ;
- délai ou urgence ;
- objections ;
- niveau d'intérêt ;
- informations manquantes ;
- prochaine action recommandée.

Sépare clairement les informations certaines
des informations qui restent inconnues.

N'invente aucune information.
""".strip()

    LEAD_QUALIFICATION = """
Analyse le contact comme un prospect commercial.

Évalue les éléments observables dans la conversation :

- besoin ;
- urgence ;
- budget ;
- autorité de décision si identifiable ;
- adéquation avec l'offre ;
- niveau d'engagement ;
- prochaine étape.

Ne donne pas un score arbitraire sans justification.

Si une information est inconnue, indique-la comme
inconnue plutôt que de l'inventer.
""".strip()

    OBJECTION_ANALYSIS = """
Identifie les objections exprimées ou implicites
dans la conversation.

Pour chaque objection identifiée :

- indique ce que le contact semble hésiter à accepter ;
- explique brièvement pourquoi cela peut constituer
  une objection ;
- propose une manière naturelle d'y répondre ;
- évite les techniques de pression ou de manipulation.

Si aucune objection claire n'est présente,
indique-le.
""".strip()

    FOLLOW_UP = """
Prépare une proposition de suivi commercial.

Le suivi doit :
- rappeler naturellement le contexte ;
- être court ;
- ne pas être insistant ;
- apporter une raison claire de reprendre contact ;
- proposer une prochaine étape simple.

N'invente jamais une information concernant
le prospect ou l'offre.
""".strip()

    MEMORY_EXTRACTION = """
À partir de la conversation fournie, identifie uniquement
les informations stables et réellement utiles à conserver
dans la mémoire de VYRA.

Exemples :
- préférence ;
- budget ;
- besoin ;
- produit recherché ;
- localisation ;
- objectif ;
- contrainte ;
- information importante concernant le projet.

Ne conserve pas :
- les salutations banales ;
- les informations sans utilité future ;
- les suppositions ;
- les informations incertaines présentées comme des faits.

Chaque information doit être directement justifiable
par la conversation.
""".strip()

    SUMMARY_GENERATION = """
Résume la conversation de manière concise.

Le résumé doit permettre à VYRA de comprendre rapidement :

- qui est le contact ;
- ce qu'il recherche ;
- ce qui a déjà été discuté ;
- ce qui reste à résoudre ;
- la prochaine étape éventuelle.

Ne crée aucune information absente de la conversation.
""".strip()

    GENERAL_ASSISTANT = """
Réponds comme un assistant professionnel qui aide
l'utilisateur à accomplir sa tâche.

Comprends d'abord le contexte.

Si la demande est ambiguë, demande uniquement
l'information nécessaire.

Ne prétends jamais avoir effectué une action externe
que tu n'as pas réellement effectuée.
""".strip()

    # ------------------------------------------------------------------
    # CONSTRUCTION
    # ------------------------------------------------------------------

    @classmethod
    def identity(
        cls,
    ) -> Prompt:
        return Prompt(
            name="assistant_identity",
            content=cls.ASSISTANT_IDENTITY,
        )

    @classmethod
    def commercial(
        cls,
    ) -> Prompt:
        return Prompt(
            name="commercial_assistant",
            content=(
                f"{cls.ASSISTANT_IDENTITY}\n\n"
                f"{cls.COMMERCIAL_ASSISTANT}"
            ),
        )

    @classmethod
    def response_generation(
        cls,
    ) -> Prompt:
        return Prompt(
            name="response_generation",
            content=(
                f"{cls.ASSISTANT_IDENTITY}\n\n"
                f"{cls.COMMERCIAL_ASSISTANT}\n\n"
                f"{cls.RESPONSE_GENERATION}"
            ),
        )

    @classmethod
    def conversation_analysis(
        cls,
    ) -> Prompt:
        return Prompt(
            name="conversation_analysis",
            content=(
                f"{cls.ASSISTANT_IDENTITY}\n\n"
                f"{cls.CONVERSATION_ANALYSIS}"
            ),
        )

    @classmethod
    def lead_qualification(
        cls,
    ) -> Prompt:
        return Prompt(
            name="lead_qualification",
            content=(
                f"{cls.ASSISTANT_IDENTITY}\n\n"
                f"{cls.LEAD_QUALIFICATION}"
            ),
        )

    @classmethod
    def objection_analysis(
        cls,
    ) -> Prompt:
        return Prompt(
            name="objection_analysis",
            content=(
                f"{cls.ASSISTANT_IDENTITY}\n\n"
                f"{cls.OBJECTION_ANALYSIS}"
            ),
        )

    @classmethod
    def follow_up(
        cls,
    ) -> Prompt:
        return Prompt(
            name="follow_up",
            content=(
                f"{cls.ASSISTANT_IDENTITY}\n\n"
                f"{cls.COMMERCIAL_ASSISTANT}\n\n"
                f"{cls.FOLLOW_UP}"
            ),
        )

    @classmethod
    def memory_extraction(
        cls,
    ) -> Prompt:
        return Prompt(
            name="memory_extraction",
            content=cls.MEMORY_EXTRACTION,
        )

    @classmethod
    def summary(
        cls,
    ) -> Prompt:
        return Prompt(
            name="summary_generation",
            content=cls.SUMMARY_GENERATION,
        )

    @classmethod
    def general(
        cls,
    ) -> Prompt:
        return Prompt(
            name="general_assistant",
            content=(
                f"{cls.ASSISTANT_IDENTITY}\n\n"
                f"{cls.GENERAL_ASSISTANT}"
            ),
        )

    # ------------------------------------------------------------------
    # CUSTOM PROMPT
    # ------------------------------------------------------------------

    @staticmethod
    def build_with_context(
        prompt: Prompt,
        *,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Ajoute un contexte structuré à un prompt.

        Cette méthode ne connaît pas Gemini.
        Elle prépare simplement le texte qui sera envoyé
        au Gateway.
        """

        if not context:
            return prompt.content

        context_lines: list[str] = []

        for key, value in context.items():
            context_lines.append(
                f"{key}: {value}"
            )

        context_text = "\n".join(context_lines)

        return (
            f"{prompt.content}\n\n"
            "CONTEXTE FOURNI PAR VYRA\n"
            "-------------------------\n"
            f"{context_text}"
        )


def get_prompt(
    name: str,
) -> Prompt:
    """
    Retourne un prompt VYRA à partir de son nom.

    Exemple :

        get_prompt("response_generation")
    """

    prompts = {
        "identity": VYRAPrompts.identity,
        "commercial": VYRAPrompts.commercial,
        "response_generation": VYRAPrompts.response_generation,
        "conversation_analysis": VYRAPrompts.conversation_analysis,
        "lead_qualification": VYRAPrompts.lead_qualification,
        "objection_analysis": VYRAPrompts.objection_analysis,
        "follow_up": VYRAPrompts.follow_up,
        "memory_extraction": VYRAPrompts.memory_extraction,
        "summary": VYRAPrompts.summary,
        "general": VYRAPrompts.general,
    }

    factory = prompts.get(name)

    if factory is None:
        available = ", ".join(sorted(prompts))

        raise ValueError(
            f"Prompt VYRA inconnu : {name!r}. "
            f"Prompts disponibles : {available}"
        )

    return factory()