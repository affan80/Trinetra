from deep_translator import GoogleTranslator


class Translator:

    def translate_to_english(self, text):

        try:

            translated = GoogleTranslator(
                source="auto",
                target="en"
            ).translate(text)

            return translated

        except:

            return text


if __name__ == "__main__":

    translator = Translator()

    text = translator.translate_to_english(
        "भारत"
    )

    print(text)