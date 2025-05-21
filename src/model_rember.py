import os

from aqt import mw

#: Constants

# WARN: The version in the model name matches the addon version in which the
# model was introduced.
NAME_MODEL_REMBER = "Rember 0.1.0"

NAME_FIELD_LINK = "Link (Do not edit)"
NAME_FIELD_NOTE = "Note (Do not edit)"
NAME_FIELD_DATA = "Data (Do not edit)"
NAME_FIELD_MEDIA = "Media (Do not edit)"
NAME_FIELD_ID_CARD = lambda ix: f"Card #{ix + 1} (Do not edit)"

NAME_TEMPLATE_MODEL_REMBER = lambda ix: f"Card #{ix + 1}"

# Arbitrary large number to accomodate Rembs with many cards or many changes to
# the cards.
CNT_MAX_ANKI_CARDS = 32

# TODO: Review
# Fields in a AnkiNote must be separated by this character.
# See NoteAnki["flds"].
SEPARATOR_ANKI = "\u001f"

#: Utils


def wrap_field_data(field_data: str) -> str:
    """Util for wrapping the data field in a pre tag, to format the field correctly in the Anki editor."""
    return f"<pre>{field_data}</pre>"


def make_template(side: str, ix: int) -> str:
    """
    The template is parsed by Anki and inserted in the review page. The template
    is HTML, therefore we can use it to inject the app-anki Svelte component in
    the page.

    REFS:
    https://docs.ankiweb.net/templates/intro.html
    https://www.reddit.com/r/Anki/comments/e005jx/load_js_functions_in_external_file/
    https://www.reddit.com/r/Anki/comments/ckahp6/es6_modules_in_ankis_javascript/
    """

    addon = mw.addonManager.addonFromModule(__name__)
    path_script_app_anki = f"/_addons/{addon}/app_anki/app-anki.umd.cjs"
    path_css_app_anki = f"/_addons/{addon}/app_anki/app-anki.css"

    template = """



{{#<FIELD_ID_CARD>}}

<script id="rember-script-template">
  var setup = async () => {
    const injectScript = (src) => {
      return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    };
    const injectCSS = (src) => {
      return new Promise((resolve, reject) => {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.type = 'text/css';
        link.href = src;
        link.onload = resolve;
        link.onerror = reject;
        document.head.appendChild(link);
      });
    };

    // Remove the Anki style tag, which interferes with app-anki.
    const styleAnki = document.querySelector('head > style');
    if (styleAnki != undefined) styleAnki.remove();

    // Remove the Anki desktop stylesheet, which interferes with app-anki.
    const linkCssAnki = document.querySelector('[href$="webview.css"]');
    if (linkCssAnki != undefined) linkCssAnki.remove();

    await injectScript('<PATH_SCRIPT_APP_ANKI>');
    await injectCSS('<PATH_CSS_APP_ANKI>');
  }

  var renderAppAnki = () => {
    // Remove the pre tag wrapping the data field string.
    const unwrapFieldData = (fieldData) => {
      const matches = fieldData.match(/<pre>([\\S\\s]*?)<\\/pre>/);
      if (matches == undefined || matches.length <= 1) {
        throw new Error("Invalid field: <FIELD_DATA>");
      }
      return matches[1];
    }

    const fieldData0 = String.raw`{{<FIELD_DATA>}}`;
    const fieldData1 = unwrapFieldData(fieldData0);
    const fieldData2 = JSON.parse(fieldData1);

    const fieldIdCard = String.raw`{{<FIELD_ID_CARD>}}`;

    // Name `AppAnki` comes from `vite.config.js` in `@rember/app-anki`
    new window.AppAnki({
      // Append app-anki after this script element, where Anki expects the
      // note content to be.
      target: document.getElementById('rember-script-template').parentElement,
      props: {
        contentRemb: fieldData2,
        idCard: fieldIdCard,
        side: '<SIDE>'
      }
    });
  }

  // Anki runs this script multiple times in the same JS environment,
  // make sure we call the 'setup' function once.
  if (window.hasSetupAppAnki) {
    renderAppAnki();
  } else {
    window.hasSetupAppAnki = true;
    setup().then(renderAppAnki);
  }
</script>

{{/<FIELD_ID_CARD>}}
"""

    return (
        template.replace("<FIELD_ID_CARD>", NAME_FIELD_ID_CARD(ix))
        .replace("<PATH_SCRIPT_APP_ANKI>", path_script_app_anki)
        .replace("<PATH_CSS_APP_ANKI>", path_css_app_anki)
        .replace("<FIELD_DATA>", NAME_FIELD_DATA)
        .replace("<SIDE>", side)
    )


#:


def create_rember_model():
    if mw.col is None:
        raise RuntimeError("Connection is None")

    models = mw.col.models

    # Skip if the model already exists
    if models.by_name(NAME_MODEL_REMBER) is not None:
        return

    ##: Create base model

    notetype = models.new(NAME_MODEL_REMBER)

    # Sort by the "Note (Do not edit)" field
    notetype["sortf"] = 1

    ##: Add fields

    field_link = models.new_field(NAME_FIELD_LINK)
    models.add_field(notetype, field_link)

    field_note = models.new_field(NAME_FIELD_NOTE)
    models.add_field(notetype, field_note)

    field_data = models.new_field(NAME_FIELD_DATA)
    field_data["font"] = "Monospace"
    field_data["size"] = 14
    models.add_field(notetype, field_data)

    field_media = models.new_field(NAME_FIELD_MEDIA)
    field_media["font"] = "Monospace"
    field_media["size"] = 14
    models.add_field(notetype, field_media)

    for ix in range(CNT_MAX_ANKI_CARDS):
        field_id_card = models.new_field(NAME_FIELD_ID_CARD(ix))
        field_id_card["font"] = "Monospace"
        field_id_card["size"] = 14
        models.add_field(notetype, field_id_card)

    ##: Add templates

    for ix in range(CNT_MAX_ANKI_CARDS):
        template_model_rember = models.new_template(NAME_TEMPLATE_MODEL_REMBER(ix))
        template_model_rember["qfmt"] = make_template("front", ix)
        template_model_rember["afmt"] = make_template("back", ix)
        template_model_rember["bqfmt"] = NAME_FIELD_NOTE
        template_model_rember["bafmt"] = NAME_FIELD_NOTE
        models.add_template(notetype, template_model_rember)

    ##:

    models.add(notetype)
