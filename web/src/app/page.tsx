import { InvestigationWorkspace } from '../components/InvestigationWorkspace'

type Props = { searchParams: Promise<{ benchmark?: string }> }

export default async function Page({ searchParams }: Props) {
  const params = await searchParams
  return <InvestigationWorkspace benchmark={params?.benchmark === '100000'} />
}
