# Arena architecture review

The review is a standalone HTML document with embedded SVG diagrams. It works
without a server or CDN. The `.puml` files are the editable UML sources;
`plan.template.html` holds the review text and presentation.

To regenerate with PlantUML 1.2026.1 and Java 17:

```sh
cd docs/arena-architecture
java -Djava.awt.headless=true -jar /path/to/plantuml-1.2026.1.jar -tsvg -nometadata \
  components.puml deployment.puml github-registration.puml domain-model.puml \
  run-sequence.puml run-state.puml
python3 build-plan.py
```

The shared style uses Smetana, so Graphviz and a remote rendering service are not
required. Build output is `../arena-architecture-review.html`; the earlier
`../arena-integration-plan.html` link is updated with the same content.

Sources are linked from each diagram, alongside a standalone SVG export. These
download links require the accompanying directory; viewing the HTML does not.
