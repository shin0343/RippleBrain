'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Loader2, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { organizationsApi } from '@/lib/organizations-api';
import { rippleBrainApi } from '@/lib/ripplebrain-api';
import type { RippleBrainAnalysis } from '@app-starter/shared';

interface PageProps {
  params: Promise<{ organizationId: string }>;
}

const DEMO_CHANGE =
  'Our refund policy changes from 30 days to 14 days effective October 15, 2026. Analyze the organizational impact.';

const severityVariant = (severity: string): 'destructive' | 'secondary' | 'default' => {
  if (severity === 'High') return 'destructive';
  if (severity === 'Medium') return 'secondary';
  return 'default';
};

export default function RippleBrainPage({ params }: PageProps) {
  const { organizationId } = use(params);
  const queryClient = useQueryClient();
  const [changeRequest, setChangeRequest] = useState(DEMO_CHANGE);
  const [analysis, setAnalysis] = useState<RippleBrainAnalysis | null>(null);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');

  const { data: organization } = useQuery({
    queryKey: ['organization', organizationId],
    queryFn: () => organizationsApi.getOrganization(organizationId),
  });

  const { data: roleInfo } = useQuery({
    queryKey: ['organization-role', organizationId],
    queryFn: () => organizationsApi.getUserRoleInOrganization(organizationId),
  });

  const { data: runs } = useQuery({
    queryKey: ['ripplebrain-runs', organizationId],
    queryFn: () => rippleBrainApi.listRuns(organizationId),
  });

  const canDecide = roleInfo?.role === 'OWNER' || roleInfo?.role === 'ADMIN';

  const analyzeMutation = useMutation({
    mutationFn: () => rippleBrainApi.analyze(organizationId, { changeRequest }),
    onSuccess: (result) => {
      setAnalysis(result);
      setError('');
      void queryClient.invalidateQueries({ queryKey: ['ripplebrain-runs', organizationId] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const decideMutation = useMutation({
    mutationFn: ({ actionId, decision }: { actionId: string; decision: 'approve' | 'reject' }) =>
      decision === 'approve'
        ? rippleBrainApi.approve(organizationId, actionId, { note })
        : rippleBrainApi.reject(organizationId, actionId, { note }),
    onSuccess: (updated) => {
      setAnalysis((prev) =>
        prev
          ? {
              ...prev,
              actions: prev.actions.map((action) =>
                action.id === (updated as { id: string }).id ? { ...action, ...(updated as object) } : action,
              ),
            }
          : prev,
      );
      setError('');
      void queryClient.invalidateQueries({ queryKey: ['ripplebrain-runs', organizationId] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleAnalyze = () => {
    if (changeRequest.trim().length < 10 || analyzeMutation.isPending) return;
    analyzeMutation.mutate();
  };

  if (!organization) {
    return (
      <PageContainer>
        <div className="mx-auto max-w-4xl px-4 py-16 text-center text-muted-foreground">
          Organization not found, or you no longer have access to it.
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="mx-auto max-w-4xl space-y-8 px-4 py-8">
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/organizations/${organizationId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {organization.name}
          </Link>
        </Button>
        <PageHeader
          title="RippleBrain"
          description="Policy impact analysis for this organization. Drafts never apply without human approval."
        />

        {!canDecide && (
          <Card>
            <CardContent className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <ShieldAlert className="h-4 w-4" />
              You can run analyses, but only organization owners and admins can approve actions.
            </CardContent>
          </Card>
        )}

        {error && (
          <Card>
            <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Change request</CardTitle>
            <CardDescription>Describe the policy change in plain language.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={changeRequest}
              onChange={(event) => setChangeRequest(event.target.value)}
              rows={3}
              aria-label="Change request"
            />
            <Button onClick={handleAnalyze} disabled={analyzeMutation.isPending}>
              {analyzeMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Analyze impact
            </Button>
          </CardContent>
        </Card>

        {analysis && (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Result</CardTitle>
                <CardDescription>
                  Retrieval: {analysis.retrieval_mode} · Tools: {analysis.selected_tools.join(', ')}
                </CardDescription>
              </CardHeader>
              <CardContent className="text-sm">{analysis.summary}</CardContent>
            </Card>

            <section className="space-y-3" aria-label="Impacts">
              <h2 className="text-lg font-medium">Organizational impact</h2>
              {analysis.impacts.map((impact) => (
                <Card key={impact.department}>
                  <CardHeader className="py-4">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="text-base">{impact.department}</CardTitle>
                      <Badge variant={severityVariant(impact.severity)}>{impact.severity}</Badge>
                    </div>
                    <CardDescription>{impact.owner}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-1 text-sm">
                    <p>{impact.description}</p>
                    <p className="text-muted-foreground">{impact.recommended_action}</p>
                  </CardContent>
                </Card>
              ))}
            </section>

            {analysis.exceptions.map((exception, index) => (
              <Card key={index}>
                <CardHeader>
                  <CardTitle>{exception.title}</CardTitle>
                  <CardDescription>
                    Clause {exception.clause} · applies through {exception.applies_through}
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-sm">{exception.explanation}</CardContent>
              </Card>
            ))}

            <section className="space-y-3" aria-label="Actions">
              <h2 className="text-lg font-medium">Action center</h2>
              {analysis.actions.map((action) => (
                <Card key={action.id}>
                  <CardHeader className="py-4">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="text-base">{action.title}</CardTitle>
                      <Badge variant="outline">{action.status}</Badge>
                    </div>
                    <CardDescription>
                      {action.department} · {action.owner} · {action.priority} priority
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <p>{action.description}</p>
                    {action.status === 'draft' && canDecide && (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          disabled={decideMutation.isPending}
                          onClick={() => decideMutation.mutate({ actionId: action.id, decision: 'approve' })}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={decideMutation.isPending}
                          onClick={() => decideMutation.mutate({ actionId: action.id, decision: 'reject' })}
                        >
                          Reject
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </section>
          </>
        )}

        <section className="space-y-3" aria-label="Audit trail">
          <h2 className="text-lg font-medium">Organization audit trail</h2>
          <Card>
            <CardContent className="space-y-1 py-4 text-xs text-muted-foreground">
              {(runs?.items.length ?? 0) === 0 && <p>No RippleBrain runs recorded for this organization yet.</p>}
              {runs?.items.map((run) => (
                <p key={run.id}>
                  {run.createdAt} · {run.kind} · {run.summary ?? run.analysisId ?? ''}
                </p>
              ))}
            </CardContent>
          </Card>
        </section>
      </div>
    </PageContainer>
  );
}
