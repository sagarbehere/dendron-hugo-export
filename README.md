# dendron-hugo-export

These are some quick-and-dirty scripts to export notes from a [Dendron](https://dendron.so) vault into a hierarchy of files and folders intended for publishing with [Huge](https://gethugo.io).

The scripts

- Export notes from a Dendron vault into a hierarchy of files/folders in the local filesystem
  - Exclude a configurable set of hierarchies and files.
  - Create `_index.md` files within folders as needed by Hugo.
  - Add the `date` frontmatter variable to each exported note, so that Hugo can set the publish date.
- Process wikilinks like `[[label | pqr.abc.xyz.md ]]` in Dendron notes into a format that is preferred by Hugo: `[label]({{< ref "pqr/abc/xyz.md" >}})`.
- Adds a Backlinks section to each note if backlinks to that note exist.

**WARNING: The scripts are extremely immature. They were cobbled together by copy/paste'ing code from StackOverflow and may fail without warning in all sorts of edge cases. I stopped working on them as soon as they started working for my own use cases. :)**
