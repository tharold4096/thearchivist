# Documentation Templates — How to Use This Folder

Nine fill-in templates, one per component of the build. Every file uses the same structure on purpose — a reader (or an interviewer) can learn the pattern once and then skim ten documents at speed, and *you* get the benefit of answering the same categories of question for every decision you made, which is what actually cements the reasoning in your own head.

**Fill these out yourself, from memory, before checking your own project notes or this chat.** The value here isn't the record — you already have that. The value is the retrieval. If you get to a blank and can't answer it, that's useful information: it means you executed that step without fully owning the reasoning behind it, and it's worth going back to actually understand before you write it down. Don't paste — reconstruct.

## The template shape

Every file has the same eight sections:

1. **Overview** — one paragraph, what this component is and what job it does in the architecture
2. **What I Configured** — the concrete settings/decisions, not narrative
3. **Why I Made This Choice** — the reasoning, including alternatives you rejected and why
4. **How I Did It** — the actual procedure, written so someone else could follow it
5. **Problems I Ran Into** — what broke, what the symptom looked like, what it turned out to be
6. **What I'd Do Differently** — hindsight. This section is what separates a portfolio from a changelog.
7. **Skills This Demonstrates** — name them plainly, this is what a reader skims for
8. **Evidence** — where the screenshots/config/logs live

## Suggested order to fill these out

Roughly the order things happened, which is also the order that builds on itself:

1. `01-bios-firmware-update.md`
2. `02-idrac-configuration.md`
3. `03-raid-storage-configuration.md`
4. `04-ram-power-tuning.md`
5. `05-opnsense-base-install.md`
6. `06-wan-lan-network-split.md`
7. `07-tailscale-remote-access.md`
8. `08-dns-hardening.md`
9. `09-proxmox-installation.md`

## When you're done

- Replace every `_[...]_` prompt with your own writing, then delete the italics
- Drop screenshots into a `screenshots/` folder alongside these and reference them in the Evidence section — `![description](screenshots/whatever.png)`
- Consider a top-level `README.md` for the repo that links all nine as a table of contents, similar to what's already in your `homelab-docs` folder — these can slot in as the detailed appendix behind that front page
