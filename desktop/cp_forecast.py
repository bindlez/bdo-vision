"""Event-only CP forecasts: exact ramp integral, payoff targets and bounded search."""
import math


def productive_days(day,delay=0,ramp=0):
    active=max(0,day-delay)
    if ramp<=0:return active
    return active*active/(2*ramp) if active<ramp else active-ramp/2


def payback_days(investment,daily,delay=0,ramp=0):
    if investment<=0:return 0
    if daily<=0:return None
    needed=investment/daily
    active=math.sqrt(2*ramp*needed) if ramp>0 and needed<=ramp/2 else needed+ramp/2
    return delay+active


def income_at(report,route,day,multiplier=1):
    return route['daily']*multiplier*productive_days(day,report['delay'],report['ramp'])


def analyze(report,selected='target',elapsed=0):
    from cp_planner import build_route,to_target
    route=next((r for r in report['routes'] if r['key']==selected),report['routes'][2])
    days=report['days'];earned=income_at(report,route,elapsed)
    investment=route['investment'];profit=earned-investment
    recovered=min(100,max(0,earned/investment*100)) if investment else 100
    thresholds=(.1,.25,.5,1)
    milestones=[{'fraction':fraction,'day':payback_days(investment*fraction,route['daily'],report['delay'],report['ramp']),
                 'earned':investment*fraction,'reached':investment>0 and earned+1e-7>=investment*fraction} for fraction in thresholds]
    scenarios=[]
    for label,multiplier in (('Cautious',.5),('Your plan',1),('Strong',1.5)):
        gain=income_at(report,route,days,multiplier)
        scenarios.append({'label':label,'multiplier':multiplier,'daily':route['daily']*multiplier,
                          'payback':payback_days(investment,route['daily']*multiplier,report['delay'],report['ramp']),
                          'earnings':gain,'difference':gain-investment})
    requirements=[]
    for day in (30,90,180,365,730):
        effective=productive_days(day,report['delay'],report['ramp'])
        total=investment/effective if effective else None
        per_cp=total/(route['deployed']*report['utilization']/100) if total is not None and route['deployed'] and report['utilization'] else None
        requirements.append({'day':day,'effectiveDays':effective,'daily':total,'perCp':per_cp})
    target_rows=[];candidate_count=1
    baseline=build_route(report,'optimized',0)
    best=baseline if baseline['cash']+1e-7>=report['reserve'] else None
    # At most 600 whole-CP targets. Never step through individual byproducts.
    for target in range(report['cp']+1,601):
        batches=math.ceil(max(0,to_target(report['cp'],report['percent'],target)-1e-7)/900)
        if batches>report['totalBatches']:break
        candidate=build_route(report,'optimized',batches)
        candidate_count+=1
        if candidate['cash']+1e-7>=report['reserve'] and (best is None or (candidate['future'],-candidate['batches'])>(best['future'],-best['batches'])):best=candidate
        if target in {report['cp']+1,report['target'],500,525,550,575,600}:
            target_rows.append({'target':target,**candidate})
    # A static bounded time series and 21 income sensitivity points.
    timeline=[]
    for day in sorted(set([0,7,30,60,90,180,365,730,days])):
        if day>3650:continue
        value=income_at(report,route,day)
        timeline.append({'day':day,'earned':value,'difference':value-investment,'cashAndIncome':route['cash']+value,
                         'recovered':min(100,value/investment*100) if investment else 100})
    sensitivity=[{'multiplier':i/10,'payback':payback_days(investment,route['daily']*i/10,report['delay'],report['ramp']),
                  'difference':income_at(report,route,days,i/10)-investment} for i in range(21)]
    breakeven=route['breakEvenDays']
    if not route['gained']:title='Keep the silver';reason='This route unlocks no new whole CP, so it has no additional CP income.'
    elif not route['deployed']:title='Give those CP a job';reason='No new CP are deployed in this plan. Unused CP cannot repay the silver given up.'
    elif not route['daily']:title='Set your income plan';reason='Enter the additional net income the new CP will actually unlock. Existing income does not count.'
    elif breakeven is not None and breakeven<=days:title='Payback fits your horizon';reason=f'The modeled investment is recovered in {breakeven:.1f} days, including setup and ramp-up.'
    else:title='A longer commitment';reason='At this income rate, cash remains ahead at the selected horizon. Compare a smaller CP target or a longer timeline.'
    return {'selected':route['key'],'title':title,'reason':reason,'elapsed':elapsed,'recovered':recovered,
            'simulatedEarned':earned,'simulatedProfit':profit,'milestones':milestones,'scenarios':scenarios,
            'requirements':requirements,'targets':target_rows,'timeline':timeline,'sensitivity':sensitivity,
            'optimized':best,'candidates':candidate_count,'reserveFeasible':best is not None,
            'grindHours':investment/report['grindRate'] if report['grindRate'] else None}
