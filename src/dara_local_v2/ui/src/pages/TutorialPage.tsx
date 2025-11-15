const steps = [
  {
    title: '1 · Collect & clean your pattern',
    bullets: [
      'Export the 2θ–intensity data in XY, XYE, RAW, or XRDML format.',
      'Trim obvious detector spikes and ensure at least 20° of coverage (per diagnostics).',
      'If you plan to add custom CIFs later, copy them into the generated ~/Documents/dara_analysis/<system>/custom_cifs folder.',
    ],
  },
  {
    title: '2 · Configure the search form',
    bullets: [
      'Part 1 mirrors Notebook Part 1: upload the pattern, set the chemical system + required/exclude elements, and choose the instrument profile.',
      'Part 2 mirrors Notebook Part 2: pick ICSD / COD / MP, adjust phase cap (max_phases) and MP hull filters, and tag the job with your name.',
      'Submitting the form uploads the file locally and places a job into the SQLite-backed queue.',
    ],
  },
  {
    title: '3 · Monitor the queue & diagnostics',
    bullets: [
      'Open the Results page to view pending/running/completed jobs; status badges update live when you refresh.',
      'Diagnostics (min/max 2θ, intensity range, point count) highlight potential issues by mirroring notebook checks.',
      'If a job fails, the error message appears next to the status badge and the Solutions panel explains that no fits are available.',
    ],
  },
  {
    title: '4 · Examine solutions & download reports',
    bullets: [
      'Each solution card embeds the Plotly refinement plot (same layout as the notebook visualization).',
      'Phase tables list every phase, its CIF source, and the refined quantities from extract_phase_info().',
      'ZIP downloads contain the HTML report, CSV summaries, JSON metadata, and CIF copies exactly like the notebook export.',
    ],
  },
]

const tips = [
  'Jobs run sequentially on this machine; large searches (200 phases) may take 10–15 minutes.',
  'All uploads and reports stay local under ~/Documents/dara_analysis — nothing leaves the workstation.',
  'If you need to cancel a job, delete it from the SQLite DB and restart the worker; queue controls are on the roadmap.',
]

export function TutorialPage() {
  return (
    <div className="page-stack">
      <div className="section-card">
        <p className="eyebrow">Tutorial</p>
        <h3>Notebook workflow, recreated for the web</h3>
        <p className="muted-text">
          These steps map directly to Part 1 + Part 2 of streamlined_phase_analysis_K2SnTe5.ipynb so researchers can run the
          same analysis without opening the notebook.
        </p>
      </div>

      {steps.map((step) => (
        <div key={step.title} className="section-card">
          <h4>{step.title}</h4>
          <ul>
            {step.bullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
        </div>
      ))}

      <div className="section-card">
        <h4>Helpful tips</h4>
        <ul>
          {tips.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default TutorialPage
