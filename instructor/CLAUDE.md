# Instructor Folder

The `instructor` folder contains files for the presenter, and the presenter removes it from the repo before delivery. Nothing in the `docs` or `demos` folders may link to or depend on anything in this folder.

## Slide Template

The PPT template is `Xebia PPT General Template.pptx`. Do not modify the template, but use it when generating the slide deck in the `docs` folder.

The copy in this folder has already been repaired. The original template shipped with a corrupt zip tail that made it unreadable by python-pptx and LibreOffice, so it was fixed by truncating the trailing 5,540,053 bytes. That repair is done, so don't repeat it and don't otherwise edit the template. If the template ever fails to open with a `BadZipFile` error, someone has swapped in the corrupt original (the copy in the presenter's Downloads folder is one); stop and ask the presenter rather than repairing it again.

## Deck Build Script

Create and maintain `build_deck.py` in this folder. It builds the PPTX in the `docs` folder from the template, and it's the only way the deck gets changed. Run it from the repository root:

```
uv run --with python-pptx python instructor/build_deck.py
```

Keep the slide list, slide content, and speaker notes in the script as plain data near the top of the file, so a change to a slide is an edit to that data and not to the layout code. Use the template's own slide layouts and placeholders rather than drawing text boxes by hand, so the deck keeps the Xebia look.

Give the script an `--inventory` option that prints the slide number and title of every slide without building anything. The headings in `PRESENTER_SCRIPT.md` must match that list line for line, so use it to check the script after any change to the deck.

After each build, regenerate the PDF with the LibreOffice command in the root `CLAUDE.md` file.

## Presenter Materials

Maintain these two files in this folder:

- `TEACHING_GUIDE.md` gives guidance on delivering the webinar: preparing the machine, running the session to time, slide-by-slide teaching notes, a run book for each demo, and how to recover when something goes wrong. Anything in a demo that only the presenter needs to know belongs here, not in the demo `README.md` files.
- `PRESENTER_SCRIPT.md` is a word-for-word script of the slide deck. The presenter will read the script during the presentation to keep things on track, so it has to sound like speech. Give each slide its own heading that matches the slide title, along with a time budget and a cue for advancing to the next slide.

## Diagrams

Diagrams for the deck live in `instructor/diagrams`. Draw them with the presenter's diagram-builder MCP server: each `.svg` is the editable source, and the `.png` export beside it is what `build_deck.py` embeds. After changing a diagram, export the PNG again, then rebuild the deck and the PDF.
