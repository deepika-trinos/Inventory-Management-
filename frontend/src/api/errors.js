// Turns any failed request into a sentence a person can read.
//
// The backend always answers errors as:
//   { "error": { "code": "...", "message": "...", "details": ... } }
// (see backend/app/core/errors.py)

const FALLBACK = 'Something went wrong. Please try again.'

export function getErrorCode(error) {
  return error?.response?.data?.error?.code ?? null
}

export function getErrorMessage(error) {
  if (!error) return FALLBACK

  // No answer at all: server down, wrong address, or no network.
  if (error.request && !error.response) {
    return error.code === 'ECONNABORTED'
      ? 'The server took too long to answer. Please try again.'
      : 'Cannot reach the server. Check your connection, or that the backend is running.'
  }

  const body = error.response?.data?.error
  if (!body) return FALLBACK

  // Validation errors: list each field's problem.
  if (body.code === 'validation_error' && Array.isArray(body.details) && body.details.length) {
    const fields = body.details.map((d) => `${fieldLabel(d.field)}: ${d.message}`)
    return `${body.message} ${fields.join('; ')}`
  }
  return body.message || FALLBACK
}

// "body.email" -> "Email"
function fieldLabel(field = '') {
  const last = String(field).split('.').pop() || 'Field'
  const words = last.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}
