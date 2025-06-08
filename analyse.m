
% Folder './dataCai/' and 'setting optimization tests' is added to path
figure;
hold on;

radius = 23; % [mm]

[x, z] = getYMidLine('./dataCai/spaceLenses/P2Top.bin', radius, 'noflip');
plot(x, z, 'LineWidth', 1.5, 'DisplayName', 'lens 1');


[p_fit, z_fit, residuals, rmse1] = fitCircle(x, z); 
plot(x, z_fit, 'LineWidth', 2.2, 'DisplayName', 'Circle: z = c_y + sqrt(r^2 - (x - c_x)^2), rmse = ' + string(rmse1));
text(10, 0.1, sprintf('c_x=%f, c_y=%f, r=%f', p_fit(1), p_fit(2), p_fit(3)));

[p_fit2, z_fit2, residuals2, rmse2] = fitBessel(x, z);
plot(x, z_fit2, 'LineWidth', 2.2, 'DisplayName', 'Bezzel: z = a + bJ_0(cx), rmse = ' + string(rmse2));
text(10, 0.3, sprintf('a=%f, b=%f, c=%f', p_fit2(1), p_fit2(2), p_fit2(3)));

Bo = (p_fit2(3)*radius)^2;
l_c = 1/p_fit2(3); % [mm]
R_curv = 2/(p_fit2(2)*p_fit2(3)^2);
text(10, 0.5, sprintf('Bo=%f, l_c=%f, R_{curv}=%f', Bo, l_c, R_curv));

ylabel('z axis [mm]');
xlabel('x axis [mm]');
grid on;
legend();
hold off;

% figure;
% stem(x, residuals, 'MarkerSize', 0.01);
% title("Residuals");
% ylabel('z axis residuals [mm]');
% grid on;


function [p_fit, z_fit, residuals, rmse] = fitBessel(x, z)
    % given a + b*J_0(c*x)
    model = @(p, x) p(1) + p(2) * besselj(0, p(3) * x);
    p_init = [mean(z), range(z), 0.05];
    
    options = optimset('TolFun', 1e-9, 'TolX', 1e-9, 'MaxIter', 1000);
    p_fit = lsqcurvefit(model, p_init, x, z, [], [], options);
    z_fit = model(p_fit, x);
    residuals = z - z_fit;
    rmse = sqrt(mean(residuals.^2));
end
function [p_fit, z_fit, residuals, rmse] = fitCircle(x, z)
    % given (x-c_x)^2 + (y-c_y)^2 = r^2
    circleModel = @(p, x_in) p(2) + sqrt(p(1)^2 - (x_in - p(3)).^2);
    p_init = [80 -80, 0]; % r, a
    
    options = optimset('TolFun', 1e-9, 'TolX', 1e-9, 'MaxIter', 1000);
    p_fit = lsqcurvefit(circleModel, p_init, x, z, [], [], options);
    z_fit = circleModel(p_fit, x);
    residuals = z - z_fit;
    rmse = sqrt(mean(residuals.^2));
end
function [x, z] = getYMidLine(fileName, r_cut, flip)
    flip = strcmp(flip, 'flip');

    [a, w, h, hconv, pxsize, ~] = read_mat_bin(fileName);
    surface = a*hconv;
    y_mid = floor(h / 2);
    x = (0:pxsize:pxsize*(w-1)) * 1e3;
    z = surface(y_mid, :) * 1e3; % [mm mm]
    
    % move the max to x=0, z=0
    if flip
        [maxZ, minZIdx] = min(movmean(z, 50));
        xAtMax = x(minZIdx);
    else
        [maxZ, maxZIdx] = max(movmean(z, 50));
        xAtMax = x(maxZIdx);
    end    
    x = x - xAtMax;
    z = z - maxZ;
    
    z = z(abs(x) <= r_cut);
    x = x(abs(x) <= r_cut);
end