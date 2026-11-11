# Presentation

This folder holds the Slidev deck for the Interactive Inference 101 presentation. It needs Node.js 22.12 or later and Bun.

## Run the deck

Install the pinned dependencies:

```bash
bun install --frozen-lockfile
```

Start the development server:

```bash
bun run dev
```

Slidev prints the slide show URL, `http://localhost:3030/`, and the presenter URL, `http://localhost:3030/presenter/`.

Build the static deck:

```bash
bun run build
```

Slidev writes the build to `dist/`.

Test the simulation engine:

```bash
bun test
```

The tests in `simulator/*.test.ts` compare the engine output with hand-written traces.

## Host on suraj.io

Build the deck, replace its generated files in the sibling `blog_contents` checkout, and build Hugo:

```bash
./publish-blog.sh
```

The script installs pinned dependencies, builds for `/kubecon-na26/` with hash routing, synchronizes `static/kubecon-na26/`, and builds the blog in `public/`. It requires Bun, Node.js, Hugo, and rsync. Set `BLOG_REPO` to use a different blog checkout. The script works from any current directory.

Publish mode commits and pushes all pending changes in both `blog_contents` and its website repository. Review both working trees before you run publish mode:

```bash
./publish-blog.sh --publish "your commit message"
```

The script uses the blog's existing `hack/build-and-publish.sh`. Set `WEB_REPO` if the website checkout is not the blog's sibling `surajssd.github.io`. After GitHub Pages finishes deployment, the slides are available at `https://suraj.io/kubecon-na26/`.

## Deck structure

`slides.md` holds the headmatter, the title slide, the speaker slides, and one `src` include for each chapter in `slides/`. The chapters follow the agenda in [docs/narrative.md](../docs/narrative.md).

| Folder | Contents |
| --- | --- |
| `slides/` | Chapters `01-intro.md` to `07-recap.md`. Speaker notes hold the timing, the planned interactions, and the reset and backup cues. |
| `layouts/` | `kubecon-title` (the KubeCon NA 2026 title frame), `chapter` (the KubeCon blue frame with the event logo for the chapter slides and the closing slide, optional prop `lesson`), `your-turn` (props `lesson`, `steps`, `minutes`), and `lesson-transition` (props `problem`, `next`) |
| `assets/kubecon/` | The KubeCon + CloudNativeCon North America 2026 logo (SVG) and the title illustration from the event brand artwork |
| `assets/speakers/` | A 320 by 320 pixel photo and a QR code (SVG) for each speaker |
| `assets/companies/` | Local CoreWeave and Microsoft logos for the title and speaker slides |
| `assets/icons/` | `pod.svg` and `sts.svg` from the labeled resource icons in the [Kubernetes icon set](https://github.com/kubernetes/community/tree/master/icons) (Apache-2.0 or CC BY 4.0), and `lws.svg`, the [LeaderWorkerSet](https://github.com/kubernetes-sigs/lws) logo from `site/static/images/logo.svg` at v1.0.0 (Apache-2.0) |
| `components/` | Simulations `ContinuousBatching` (A), `PrefillDecode` (B, prop `preset`), `KvCache` (C), and `LatencyThroughput` (D), plus the diagrams and shared controls. `Speakers` holds the speaker details for the second slide and the last slide. |
| `simulator/` | `batching.ts` for Simulation A, `serving.ts` for the timed engine behind B to D, `metrics.ts`, and the presets in `scenarios.ts` |
| `composables/` | `usePlayback` for timed playback, and the request color helper |

`assets/icons/linkedin-in-white.png` is the unmodified `InBug-White.png` from [LinkedIn's official logo download](https://brand.linkedin.com/downloads). The speaker link uses the white version under [LinkedIn's profile-link guidelines](https://brand.linkedin.com/in-logo).

`assets/companies/coreweave-white.svg` uses the CoreWeave SVG from the marimo gateway with white artwork and empty margins removed. `assets/companies/microsoft-white.svg` uses the [Microsoft logo SVG from Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Microsoft_logo_(2012).svg), with the wordmark changed to white for dark backgrounds. Both logos retain their original proportions and use vector artwork.

`assets/companies/vllm.svg` and `assets/companies/vllm-dark.svg` are the unmodified full logos from the [official vLLM media kit](https://github.com/vllm-project/media-kit/tree/79b2ea5db25b723f2d81dae203a87c5b9a076722). The slide selects the logo for the current light or dark mode.

`assets/companies/vllm-mark.svg` is the unmodified compact `vLLM-Logo.svg` from the same media kit revision. The shared GPU icon uses the compact mark inside its chip outline.

The engines are deterministic TypeScript with no Vue imports. The components only render engine state and send engine commands.

## Before the talk

1. Check that the link and QR code on both sign-in slides in `slides/01-intro.md` open the workspace.
2. Run `nvidia-smi topo -m` on a workshop node and check for an RDMA network. Adjust the hardware slide's speaker notes to match.
3. Build the deck and open it once with the network turned off.
4. At the room check, look at the projected deck under the room lights. If the dark slides look washed out, press `d` to switch to light mode.

## Offline operation

The deck bundles the Roboto font from `@fontsource-variable/roboto` and uses Menlo for code. Menlo is a macOS system font that cannot be bundled, so other systems fall back to their own monospace font. The deck disables Slidev's remote fonts and favicon. The build makes no external requests. Keep `fonts.provider: none` and `favicon: false` in `slides.md`, and put any new media in this folder.

## Light and dark mode

The deck has a dark mode and a light mode. It follows the system appearance until you press `d` or click the mode icon in the navigation bar. Slidev saves the choice in the browser, so the presenter and audience windows in the same browser switch together, and the choice stays after a reload. When the choice matches the system appearance, Slidev follows the system appearance again.

The title slide, the chapter slides, and the closing slide stay KubeCon blue in both modes, as in the event template.

The color tokens in `styles/index.css` hold both palettes. The light ink, request, accent, and live colors keep at least 4.5:1 contrast as text on white and under white text. When you add a color to a component, use a token:

- Use `--req-1` to `--req-6`, `--accent`, and `--live` for colored text and fills.
- Use `--ink-inverse` for text on a colored fill or on an `--ink` fill.
- Use `rgb(var(--tint) / <alpha>)` for a faint tint. It is white in dark mode and navy in light mode.

## Presenter and audience windows

Slidev synchronizes slide navigation between the presenter window and the audience window. It does not synchronize component state. Each window runs its own copy of each component, so a click in the presenter window does not change the projected component. Operate interactive components only in the projected audience window.

A component keeps its state when you leave its slide and return. Reloading the page resets it.

## Interactive components

- Do not put controls in the bottom-left corner of a slide. Slidev's navigation bar covers that corner, and it catches clicks even while it is hidden.
- Do not let a mouse click give a button focus. Slidev ignores navigation keys while a button has focus, so the presenter's clicker stops working. Add `@mousedown.prevent` to the element that holds the buttons.
- Pause playback when the presenter leaves the slide. Use `onSlideLeave` from `@slidev/client`.
