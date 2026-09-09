# Native white-background themes

| ID | Reading use | Body / line height |
|---|---|---|
| `dasen-default` | Clear everyday prose; existing baseline | 16px / 1.6 |
| `dasen-reading` | Spacious continuous reading | 18px / 1.8 |
| `dasen-document` | Compact technical explanations, lists and tables | 16px / 1.7 |

All use the native renderer and `dasen-light` syntax palette. Select per article or channel; a new theme does not silently change a project default. Main backgrounds remain white, with restrained headings and no decorative shadows or background textures. Local visual checks cover the sample article at phone widths; a local preview does not establish WeChat phone acceptance.

## Design references and provenance

These YAML definitions are independently authored changes to the existing original Dasen baseline, under the repository MIT license. No external CSS, font files, icons or renderer code is included.

The design review on 2026-09-09 examined the general spacing, hierarchy and table behavior of:

- [MWeb Bear](https://github.com/imageslr/mweb-themes/blob/a755840a128657dd63bd7284cf9999f778510209/src/themes/core/mweb-bear.scss). Its package metadata declares ISC, but its multi-source theme library is not treated as a blanket license for all upstream code. MWeb's official theme directory links to the collection.
- [Maple](https://github.com/xbmlz/hexo-theme-maple/blob/34669b318b21ac942377efba19f7df2b06b25cf1/LICENSE), licensed CC BY-NC-SA 4.0. General simplicity and whitespace informed the brief; its CSS is not copied or relicensed.
- [Doocs default](https://github.com/doocs/md/blob/a9d3da04ccc3a06e347c47f1192f1f6689eee74f/packages/shared/src/configs/theme-css/default.css), whose repository uses WTFPL v2. Its colored heading blocks are outside this collection's white/simple brief.

Repository stars and inclusion in an editor are adoption signals for a project, not a reliable popularity ranking of individual themes. No theme is advertised as the most popular.
