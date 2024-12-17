basepath1 = '/p/tmp/dominikp/COMPASS/Meteo_data/Wind_combined/';
basepath2 = '/p/tmp/dominikp/COMPASS/Meteo_data/Wind_combined_detrended/';

% tsEVA toolbox from Mentaschi et al. (2016), download from https://github.com/menta78/tsEva/
addpath('/p/projects/flooddrivers/Delft3D/SLR_GIA/tsEva-master')

t1 = datetime(1950,1,1,1,0,0);
t2 = datetime(2023,12,31,23,0,0);
timeframe = t1:hours(1):t2;
dates = datenum(timeframe)';

for i=0:99

    filename = strcat(basepath1,'sfcWind_ERA5_',num2str(i),'.nc');
    savename = strcat(basepath2,'sfcWind_detrended_ERA5_',num2str(i),'.nc');

    ws = ncread(filename,'sfcWind');
    ws_1950 = ws;

    for x=1:size(ws,1)
        for y=1:size(ws,2)

            ws_g = squeeze(ws(x,y,:));
            ws_g_1950 = ws_g;

            % tsEVA
            minPeakDistanceInDays = 3;
            timeWindow = 365.25*30;
            [param_ts, data_ts] = tsEvaNonStationary([dates ws_g], ...
            timeWindow, 'potPercentiles', [99], 'transfType', 'seasonal', ...
            'minPeakDistanceInDays', minPeakDistanceInDays);

            % if seasonal fails, try with only overall trend
            if isempty(param_ts)
                [param_ts, data_ts] = tsEvaNonStationary([dates ws_g], ...
                timeWindow, 'potPercentiles', [99], 'transfType', 'trend', ...
                'minPeakDistanceInDays', minPeakDistanceInDays);
            else
            end

            % 1950 transformation
            k = param_ts(2).parameters.epsilon;
            for d=1:size(ws_g,1)
                ws_g_d = ws_g(d);
                theta = param_ts(2).parameters.threshold(d);
                if ws_g_d >= theta
                    sigma = param_ts(2).parameters.sigma(d);
                    Perc = cdf('GeneralizedPareto',ws_g_d,k,sigma,theta);
                    if Perc > 0
                        date_d = datevec(timeframe(d));
                        date_d_1950 = datetime(1950,date_d(2),date_d(3),date_d(4),0,0);
                        start_loc = find(timeframe==date_d_1950);
                        sigma1 = param_ts(2).parameters.sigma(start_loc);
                        theta1 = param_ts(2).parameters.threshold(start_loc);
                        ws_g_1950(d,1) = icdf('GeneralizedPareto',Perc,k,sigma1,theta1);
                    end
                end
            end
            ws_1950(x,y,:)=ws_g_1950;
        end
    end
    S = ncinfo(filename);
    ncwriteschema(savename,S)
    ncwrite(savename,'sfcWind',ws_1950)
    ncwrite(savename,'time',ncread(filename,'time'))
    ncwrite(savename,'lon',ncread(filename,'lon'))
    ncwrite(savename,'lat',ncread(filename,'lat'))
end