import json
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf,plot_pacf
from statsmodels.stats.diagnostic import acorr_ljungbox
from sklearn.ensemble import RandomForestRegressor
from .common import ROOT,SEED,download,write_json,table,figure,report,environment,plt
MODELS=['Naive','Drift','ARIMA(1,1,1)','Damped ETS','Random Forest lags']

def load_series():
    path=download('https://api.worldbank.org/v2/country/IDN/indicator/FP.CPI.TOTL?date=1970:2024&format=json&per_page=1000','indonesia_cpi.json')
    raw=json.loads(path.read_text())
    df=pd.DataFrame([{'year':int(r['date']),'cpi':r['value']} for r in raw[1]]).sort_values('year')
    assert df.year.is_unique and df.cpi.notna().all() and (df.cpi>0).all()
    assert np.array_equal(df.year.to_numpy(),np.arange(1970,2025))
    df.to_csv(ROOT/'data/processed/annual_cpi.csv',index=False)
    write_json('data_audit.json',{'rows':len(df),'start':1970,'end':2024,'missing':int(df.cpi.isna().sum()),'frequency':'annual','unit':'CPI 2010=100','api_metadata':raw[0],'seasonal_models':'not identifiable for annual observations; no SARIMA/STL/Holt-Winters seasonality imposed'})
    return pd.Series(df.cpi.to_numpy(),index=pd.Index(df.year,name='year'),name='cpi')

def forecast(model,series,h):
    y=np.log(np.asarray(series,dtype=float))
    interval=None
    if model=='Naive':
        pred=np.repeat(y[-1],h); residual=np.diff(y)
    elif model=='Drift':
        drift=(y[-1]-y[0])/(len(y)-1)
        pred=y[-1]+np.arange(1,h+1)*drift; residual=np.diff(y)-drift
    elif model=='ARIMA(1,1,1)':
        fit=ARIMA(y,order=(1,1,1),trend='t').fit()
        fc=fit.get_forecast(h)
        pred=fc.predicted_mean
        interval=np.exp(np.asarray(fc.conf_int(alpha=.05)))
        residual=np.asarray(fit.resid)[2:]
    elif model=='Damped ETS':
        fit=ExponentialSmoothing(y,trend='add',damped_trend=True,initialization_method='estimated').fit(optimized=True)
        pred=fit.forecast(h); residual=np.asarray(fit.resid)
    elif model=='Random Forest lags':
        # Predict log growth rather than CPI level, using only past growth lags.
        growth=np.diff(y)
        X=np.array([growth[i-3:i][::-1] for i in range(3,len(growth))])
        target=growth[3:]
        fit=RandomForestRegressor(n_estimators=150,max_depth=3,min_samples_leaf=3,random_state=SEED,n_jobs=1).fit(X,target)
        history=list(growth)
        predicted=[]
        for _ in range(h):
            step=float(fit.predict(np.array(history[-3:][::-1]).reshape(1,-1))[0])
            history.append(step);predicted.append(step)
        pred=y[-1]+np.cumsum(predicted)
        residual=target-fit.predict(X)
    else:raise ValueError(model)
    return np.exp(np.asarray(pred)),residual,interval

def errors(actual,pred):
    a=np.asarray(actual); p=np.asarray(pred)
    return {'mae':np.mean(abs(a-p)),'rmse':np.sqrt(np.mean((a-p)**2)),'mape_pct':100*np.mean(abs((a-p)/a))}

def run():
    series=load_series()
    train=series.loc[:2021]
    test=series.loc[2022:2024]
    rows=[];predictions=[]
    for origin in [2009,2012,2015,2018]:
        past=train.loc[:origin]
        actual=train.loc[origin+1:origin+3]
        for model in MODELS:
            pred,_,_=forecast(model,past,len(actual))
            rows.append({'origin':origin,'model':model,**errors(actual,pred)})
            for year,a,p in zip(actual.index,actual,pred):predictions.append(dict(origin=origin,year=int(year),model=model,actual=a,predicted=p))
    backtest=pd.DataFrame(rows)
    compare=backtest.groupby('model',sort=False)[['mae','rmse','mape_pct']].mean().reset_index().sort_values('rmse')
    selected=compare.iloc[0].model
    table('rolling_origin_metrics.csv',backtest)
    table('backtest_predictions.csv',pd.DataFrame(predictions))
    table('model_comparison.csv',compare)
    pred,residual,_=forecast(selected,train,len(test))
    test_metrics=errors(test,pred)
    table('test_predictions.csv',pd.DataFrame({'year':test.index,'actual':test.to_numpy(),'forecast':pred}))
    future,_,interval=forecast(selected,series,3)
    future_table=pd.DataFrame({'year':[2025,2026,2027],'forecast':future})
    if interval is not None:
        future_table['lower95']=interval[:,0];future_table['upper95']=interval[:,1]
    table('forecast_from_2024.csv',future_table)
    diagnostics=[]
    for label,values in [('log_level',np.log(train)),('log_difference',np.log(train).diff().dropna())]:
        stat,pvalue,*_=adfuller(values,autolag='AIC',result_object=False)
        diagnostics.append(dict(series=label,adf_stat=stat,p_value=pvalue))
    table('stationarity.csv',pd.DataFrame(diagnostics))
    lb=acorr_ljungbox(residual,lags=[5],return_df=True).reset_index(names='lag')
    table('residual_ljung_box.csv',lb)
    growth=np.log(train).diff().dropna()
    mad=np.median(abs(growth-growth.median()))
    robust_z=.67449*(growth-growth.median())/mad
    table('training_growth_anomalies.csv',pd.DataFrame({'year':growth.index,'log_growth':growth.values,'robust_z':robust_z.values,'flag':abs(robust_z.values)>3.5}))
    fig,ax=plt.subplots(figsize=(10,4))
    ax.plot(train.index,train,label='Train through 2021')
    ax.plot(test.index,test,label='Held-out actual',marker='o')
    ax.plot(test.index,pred,label=f'Holdout forecast: {selected}',marker='s')
    ax.axvline(2021.5,color='gray',linestyle='--')
    ax.set(title='Indonesia consumer price index | historical holdout',ylabel='CPI (2010=100)',xlabel='Year')
    ax.legend();figure('test_forecast.png')
    fig,ax=plt.subplots(figsize=(9,4))
    ax.plot(series.loc[2000:].index,series.loc[2000:],label='Observed through 2024')
    ax.plot(future_table.year,future,label=f'Forecast from 2024: {selected}',marker='o')
    if interval is not None:ax.fill_between(future_table.year,interval[:,0],interval[:,1],alpha=.2,label='Model-based 95% interval')
    ax.set(title='Retrospective forecast from a fixed 2024 cutoff',ylabel='CPI (2010=100)',xlabel='Year');ax.legend();figure('future_forecast.png')
    fig,axes=plt.subplots(2,1,figsize=(9,6))
    log=np.log(train)
    trend=log.rolling(5,center=True).mean()
    axes[0].plot(log.index,log,label='Log CPI');axes[0].plot(trend.index,trend,label='Centered 5-year descriptive trend');axes[0].legend()
    axes[1].plot(log.index,log-trend);axes[1].set(title='Detrended remainder | no annual seasonal component',xlabel='Year')
    figure('trend_diagnostics.png')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    plot_acf(growth,lags=12,ax=axes[0]);plot_pacf(growth,lags=12,ax=axes[1],method='ywm');figure('acf_pacf.png')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].plot(residual);axes[0].axhline(0,color='gray');axes[0].set(title=f'{selected}: training residuals',ylabel='Log scale',xlabel='Observation')
    plot_acf(residual,lags=12,ax=axes[1]);figure('residual_diagnostics.png')
    result={'selected_model':selected,'selection':'mean rolling-origin RMSE; fixed models; no test selection','test_years':[2022,2023,2024],'test_metrics':test_metrics,'forecast_cutoff':2024,'forecast':future_table.to_dict('records'),'ljung_box_p':float(lb.lb_pvalue.iloc[0])}
    write_json('metrics.json',result)
    report('Forecasting Indonesian CPI with Statistical and Machine Learning Models',{
        'Question and data':'Forecast annual Indonesian CPI (2010=100), World Bank/IMF 1970–2024. Fixed historical cutoff; 2025–2027 forecasts are retrospective scenarios and are not current advice. Annual frequency cannot identify within-year seasonality; no artificial SARIMA seasonal period is imposed.',
        'Validation design':'Expanding rolling origins 2009, 2012, 2015, 2018 with three-year horizons. Select lowest mean RMSE before final holdout 2022–2024. Models: naive, log drift, ARIMA(1,1,1) with drift, damped ETS on log CPI, and recursive random forest on three past log-growth lags.',
        'Actual results':f'Selected {selected}. Holdout MAE {test_metrics["mae"]:.3f} CPI points; RMSE {test_metrics["rmse"]:.3f}; MAPE {test_metrics["mape_pct"]:.2f}%. Training residual Ljung–Box lag-5 p={result["ljung_box_p"]:.4g}.\n\n'+compare.to_markdown(index=False),
        'Interpretation and recommendations':'CPI levels and inflation rates are distinct. Exponentiated log forecasts are median-scale forecasts, not bias-corrected means. Use annual estimates for broad scenario planning; obtain monthly data for seasonal decisions. Crisis observations are flagged, retained and not automatically removed. ADF/Ljung–Box are diagnostic tools, not proofs of validity.',
        'Limitations and Future Work':'Few observations, structural breaks and revised latest-vintage historical data. Backtest is not real-time vintage evaluation. No exogenous predictors. Forecast intervals are supplied only when the selected ARIMA model provides model-based intervals; other models have point forecasts, not fabricated intervals. Future: monthly CPI, broader origin sensitivity, interval calibration and real-time vintage data.'},[
        f'Compared five annual CPI forecasting models across four rolling origins and a three-year held-out period.',
        f'Selected {selected} using pre-test RMSE; achieved held-out RMSE {test_metrics["rmse"]:.3f} CPI points with ADF and residual diagnostics.'])
    environment(['numpy','pandas','scipy','statsmodels','scikit-learn','matplotlib','nbformat','tabulate'])
    print(json.dumps(result,indent=2),flush=True)
    return result
if __name__=='__main__':run()
