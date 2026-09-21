"""Present the final continuation's sealed, current numerical records."""


def append_next_results(source, panel, number):
    current = source('next-research-summary', 'next', 'PUBLIC-RESULTS.json',
                     'latest projected-count, isolated public-CNF, pipe, reuse and regression results')
    if current['status'] != 'verified_with_explicit_limitations':
        raise ValueError('Continuation evidence has not been finalized')
    labels = {'bucket_natural':'Python natural order','bucket_min_fill':'Python min-fill',
              'array_min_fill':'Exact arrays, min-fill','cudd_natural':'CUDD natural order',
              'cudd_dynamic':'CUDD dynamic order'}
    for key,title,group,default in (
        ('projected-count-new','Distinct projected assignments','synthetic','adjacent_exclusion-48 / projected'),
        ('additional-public-count','Additional full and projected CNF cases','public','additional-01 / full')):
        rows=[]
        for index,r in enumerate(current[group]):
            item=dict(case=r['case']+' / '+r['mode'],q=32,method=r['method'],label=labels[r['method']],
                      status=r['status'],source='next-research-summary',selector=f'{group}[{index}]')
            if r['status']=='complete': item.update(cold_ms=r['cold_ms'],warm_ms=r['warm_ms'])
            else: item['reason']=r['reason']
            rows.append(item)
        panel(key,title,'Exact integer answers for the unchanged 32-request trace; full and projected contracts are separate.',
              current[group+'_scope'],current[group+'_note'],rows,default,32)
    rows=[]
    for index,r in enumerate(current['pipes']):
        case=f"n{r['n']} / {'slow' if r['delay_s'] else 'unthrottled'} reader / {'cancel' if r['cancel'] else 'complete'}"
        method='chunk_'+str(r['width'])
        label='Complete output' if r['width']==r['n'] else str((1 << r['width'])//8)+'-byte chunks'
        rows.append(dict(case=case,q=1,method=method,label=label,status='complete',source='next-research-summary',
            selector=f'pipes[{index}]',cold_ms=r['median_total_ms'],reader_first_ms=r['median_first_consumed_ms'],
            rss_upper_mib=r['median_rss_upper_mib']))
    panel('pipe-consumer-new','A separate pipe consumer','Producer and reader verify the same full output or cancelled prefix.',
          current['pipe_scope'],current['pipe_note'],rows,'n24 / slow reader / complete',
          metrics=['cold_ms','reader_first_ms','rss_upper_mib'])
    rows=[]
    for index,r in enumerate(current['preparation']):
        rows.append(dict(case=f"{r['family']} / n{r['n']}",q=r['q'],method=r['method'],
            label={'fresh_compile':'Compile existing expression','checked_structural_reload':'Checked JSON reload and compile','resident':'Reuse retained plan'}[r['method']],
            status='complete',source='next-research-summary',selector=f'preparation[{index}]',
            call_ms=r['median_total_ms'],initial_inclusive_ms=r['median_with_initial_setup_ms']))
    panel('preparation-reuse-new','Preparation and retained-plan reuse','Checked inert JSON reload recompiles; no compiled-plan persistence is claimed.',
          current['preparation_scope'],current['preparation_note'],rows,'affine / n512',32,
          metrics=['call_ms','initial_inclusive_ms'])
    for key in ('pipe_rows','soak_queries','soak_seconds','final_passed_tests','final_failed_or_error_tests','new_regressions'):
        number('next.'+key,current['headlines'][key],'int','next-research-summary','headlines.'+key)
    return current['disposition']
