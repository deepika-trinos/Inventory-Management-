// Friendly message when there is nothing to show yet (PRD 13: "useful empty states"),
// optionally with a button such as "Add the first vendor".
import InboxOutlined from '@mui/icons-material/InboxOutlined'
import { Stack, Typography } from '@mui/material'

export default function EmptyState({ title = 'Nothing here yet', message, action, icon: Icon = InboxOutlined }) {
  return (
    <Stack spacing={1} sx={{ alignItems: 'center', textAlign: 'center', py: 5, px: 2, color: 'text.secondary' }}>
      <Icon sx={{ fontSize: 40 }} />
      <Typography variant="subtitle1" sx={{ color: 'text.primary' }}>
        {title}
      </Typography>
      {message ? <Typography variant="body2">{message}</Typography> : null}
      {action ?? null}
    </Stack>
  )
}
