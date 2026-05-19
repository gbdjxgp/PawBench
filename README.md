# pawbench

An open benchmark for evaluating AI agents on real-world tasks across **150
tasks**, **6 source datasets**, and **3 agent harnesses**.

- 🌐 Website / leaderboard: <https://agentscope-ai.github.io/pawbench/>
- 📂 Tasks: [`data/pawbench-v1.0/tasks/`](data/pawbench-v1.0/tasks/)
- 🛠️ Runner & agents: separate repository

## Repository layout

```
pawbench/
├── data/
│   ├── mapping.csv                  T-id ↔ source dataset mapping
│   └── pawbench-v1.0/
│       ├── tasks/                   150 task markdown files
│       └── assets/                  workspace files mounted into agent containers
├── site/                            GitHub Pages site (Astro + React + Tailwind)
│   └── README.md                    site dev/deploy guide
├── submissions/                     (optional) per-(model, harness) result JSONs
└── .github/workflows/
    └── deploy-site.yml              auto-deploy site on push to main
```

See [`site/README.md`](site/README.md) for site development and deployment, and
[`data/pawbench-v1.0/tasks/`](data/pawbench-v1.0/tasks/) for the task format.
