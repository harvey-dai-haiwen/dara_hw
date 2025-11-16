import { useState } from 'react'
import { Link } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import SectionCard from '../components/SectionCard'

const searchSchema = z.object({
  pattern_file: z
    .custom<FileList>((files) => files instanceof FileList && files.length > 0, {
      message: 'Pattern file is required',
    })
    .refine((files) => files?.item(0)?.size, 'Pattern file is required'),
  chemical_system: z.string().min(1, 'Chemical system is required'),
  required_elements: z.string().optional().default(''),
  exclude_elements: z.string().optional().default(''),
  wavelength: z.string().min(1, 'Wavelength is required'),
  instrument_profile: z.string().min(1, 'Instrument profile is required'),
  database: z.enum(['ICSD', 'COD', 'MP']),
  mp_experimental_only: z.boolean().default(false),
  mp_max_e_above_hull: z.coerce
    .number({ invalid_type_error: 'Provide a numeric hull value' })
    .min(0, 'Must be ≥ 0')
    .max(2, 'Must be ≤ 2'),
  max_phases: z.coerce
    .number({ invalid_type_error: 'Provide a numeric count' })
    .min(50, 'At least 50 phases')
    .max(800, 'Keep below 800 phases'),
  user: z.string().min(1, 'Please enter your name or initials'),
  // Optional field handled in the UI; schema keeps it flexible.
  custom_cifs: z.any().optional(),
})

type SearchFormValues = z.infer<typeof searchSchema>

type SubmitResult =
  | { status: 'success'; jobId: string }
  | { status: 'error'; message: string }
  | null

const wavelengthOptions = ['Cu', 'Co', 'Mo']
const instrumentProfiles = ['Aeris-fds-Pixcel1d-Medipix3']
const databaseOptions: Array<'ICSD' | 'COD' | 'MP'> = ['ICSD', 'COD', 'MP']

function parseElementList(value?: string): string[] {
  if (!value) return []
  return value
    .split(/[,\s]+/)
    .map((token) => token.trim())
    .filter(Boolean)
}

export function SearchPage() {
  const [submitResult, setSubmitResult] = useState<SubmitResult>(null)

  const {
    register,
    handleSubmit,
    resetField,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SearchFormValues>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      chemical_system: '',
      required_elements: 'Y, Mo, O',
      exclude_elements: '',
      wavelength: 'Cu',
      instrument_profile: 'Aeris-fds-Pixcel1d-Medipix3',
      database: 'ICSD',
      mp_experimental_only: false,
      mp_max_e_above_hull: 0.1,
      max_phases: 200,
      user: '',
    },
    mode: 'onBlur',
  })

  const patternFile = watch('pattern_file')
  const chosenFileName = patternFile?.item(0)?.name
  const customCifFiles = (watch('custom_cifs') as FileList | undefined) ?? undefined
  const customCifNames = customCifFiles ? Array.from(customCifFiles).map((file) => file.name) : []

  const onSubmit = async (values: SearchFormValues) => {
    setSubmitResult(null)
    const file = values.pattern_file.item(0)
    if (!file) {
      setSubmitResult({ status: 'error', message: 'Pattern file missing' })
      return
    }

    const formData = new FormData()
    formData.append('pattern_file', file, file.name)
    formData.append('user', values.user.trim())
    formData.append('chemical_system', values.chemical_system.trim())
    formData.append('required_elements', JSON.stringify(parseElementList(values.required_elements)))
    formData.append('exclude_elements', JSON.stringify(parseElementList(values.exclude_elements)))
    formData.append('wavelength', values.wavelength)
    formData.append('instrument_profile', values.instrument_profile)
    formData.append('database', values.database)
    formData.append('mp_experimental_only', String(values.mp_experimental_only))
    formData.append('mp_max_e_above_hull', String(values.mp_max_e_above_hull))
    formData.append('max_phases', String(values.max_phases))

    const customCifsList = (values as SearchFormValues & { custom_cifs?: FileList }).custom_cifs
    if (customCifsList && customCifsList.length > 0) {
      for (let index = 0; index < customCifsList.length; index += 1) {
        const cifFile = customCifsList.item(index)
        if (cifFile) {
          formData.append('custom_cifs', cifFile, cifFile.name)
        }
      }
    }

    try {
      const response = await fetch('/api/jobs', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}))
        throw new Error(errorPayload.detail || 'Job submission failed')
      }

      const data: { job_id: string } = await response.json()
      setSubmitResult({ status: 'success', jobId: data.job_id })
      resetField('pattern_file')
    } catch (error) {
      setSubmitResult({
        status: 'error',
        message:
          error instanceof Error ? error.message : 'Unable to submit search. Please try again in a moment.',
      })
    }
  }

  return (
    <form className="page-stack" onSubmit={handleSubmit(onSubmit)} encType="multipart/form-data">
      <SectionCard title="Part 1 – Pattern & Setup" subtitle="Notebook Part 1">
        <div className="form-grid">
          <div className="form-field" style={{ gridColumn: '1 / -1' }}>
            <label htmlFor="pattern_file">Pattern file</label>
            <div className="upload-field">
              <input
                id="pattern_file"
                type="file"
                accept=".xy,.xrdml,.xye,.raw,.dat,.txt"
                {...register('pattern_file')}
              />
              {chosenFileName && <p className="file-name">{chosenFileName}</p>}
            </div>
            {errors.pattern_file && <span className="helper-text">{errors.pattern_file.message}</span>}
          </div>

          <div className="form-field" style={{ gridColumn: '1 / -1' }}>
            <label htmlFor="custom_cifs">Custom CIFs (optional)</label>
            <div className="upload-field">
              <input
                id="custom_cifs"
                type="file"
                accept=".cif"
                multiple
                {...register('custom_cifs')}
              />
              {customCifNames.length > 0 && (
                <p className="file-name">{customCifNames.join(', ')}</p>
              )}
            </div>
            <p className="field-note">
              Optional: upload one or more CIF files to be included as additional phases. Leave empty if not needed.
            </p>
          </div>

          <div className="form-field">
            <label htmlFor="chemical_system">Chemical system</label>
            <input id="chemical_system" placeholder="e.g. Y-Mo-O" {...register('chemical_system')} />
            <p className="field-note">Use dashes to separate elements. Example: Y-Mo-O.</p>
            {errors.chemical_system && <span className="helper-text">{errors.chemical_system.message}</span>}
          </div>

          <div className="form-field">
            <label htmlFor="required_elements">Required elements</label>
            <input
              id="required_elements"
              placeholder="Comma separated (Y, Mo, O)"
              {...register('required_elements')}
            />
            <p className="field-note">Elements that must appear in each candidate phase.</p>
          </div>

          <div className="form-field">
            <label htmlFor="exclude_elements">Exclude elements</label>
            <input
              id="exclude_elements"
              placeholder="Optional (Cl, Na)"
              {...register('exclude_elements')}
            />
            <p className="field-note">Elements to remove from the candidate pool.</p>
          </div>

          <div className="form-field">
            <label htmlFor="wavelength">Wavelength</label>
            <select id="wavelength" {...register('wavelength')}>
              {wavelengthOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="instrument_profile">Instrument profile</label>
            <select id="instrument_profile" {...register('instrument_profile')}>
              {instrumentProfiles.map((profile) => (
                <option key={profile} value={profile}>
                  {profile}
                </option>
              ))}
            </select>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Part 2 – Database & Filters" subtitle="Notebook Part 2">
        <div className="form-grid">
          <div className="form-field">
            <label htmlFor="database">Database</label>
            <select id="database" {...register('database')}>
              {databaseOptions.map((db) => (
                <option key={db} value={db}>
                  {db}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="max_phases">Max phases</label>
            <input id="max_phases" type="number" min={10} max={800} {...register('max_phases')} />
            <p className="field-note">Controls how many candidate phases feed into refine + search.</p>
            {errors.max_phases && <span className="helper-text">{errors.max_phases.message}</span>}
          </div>

          <div className="form-field">
            <label htmlFor="mp_max_e_above_hull">MP E-above-hull (eV)</label>
            <input
              id="mp_max_e_above_hull"
              type="number"
              step="0.01"
              min={0}
              max={2}
              {...register('mp_max_e_above_hull')}
            />
            <p className="field-note">Applied when database = MP. Default matches notebook (0.10).</p>
            {errors.mp_max_e_above_hull && (
              <span className="helper-text">{errors.mp_max_e_above_hull.message}</span>
            )}
          </div>

          <div className="form-field" style={{ gridColumn: '1 / -1' }}>
            <label className="checkbox-row">
              <input type="checkbox" {...register('mp_experimental_only')} />
              <span>MP experimental entries only</span>
            </label>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Submit" subtitle="Queue this job">
        {submitResult && (
          <div className={`status-banner ${submitResult.status}`}>
            {submitResult.status === 'success' ? (
              <>
                <div>
                  <strong>Job queued!</strong> ID: {submitResult.jobId}
                </div>
                <div className="status-links">
                  <Link to={`/results/${submitResult.jobId}`}>View detail</Link>
                  <Link to="/results">Go to queue</Link>
                </div>
              </>
            ) : (
              <div>
                <strong>Submission failed.</strong> {submitResult.message}
              </div>
            )}
          </div>
        )}

        <div className="form-grid">
          <div className="form-field">
            <label htmlFor="user">Your name</label>
            <input id="user" placeholder="Used to tag jobs" {...register('user')} />
            {errors.user && <span className="helper-text">{errors.user.message}</span>}
          </div>
          <div className="form-field">
            <label>Queue status</label>
            <p className="muted-text">Jobs execute sequentially in the backend worker. Multiple users share the queue.</p>
          </div>
        </div>

        <div className="form-actions">
          <p className="muted-text">Uploads stay on this machine only. Large searches may take 10–15 minutes.</p>
          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Submitting…' : 'Submit search'}
          </button>
        </div>
      </SectionCard>
    </form>
  )
}

export default SearchPage
