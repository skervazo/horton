// Horton is a Density Functional Theory program.
// Copyright (C) 2011-2013 Toon Verstraelen <Toon.Verstraelen@UGent.be>
//
// This file is part of Horton.
//
// Horton is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version 3
// of the License, or (at your option) any later version.
//
// Horton is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, see <http://www.gnu.org/licenses/>
//
//--


#include <cmath>
#include <cstddef>
#include "mask.h"


double switch_fn(double x, double a) {
    x /= a;
    if (x<-1) return 1.0;
    if (x>1) return 0.0;
    return 0.25*x*(x*x-3)+0.5;
}


void multiply_dens_mask(double* rho, double rho0, double alpha, double* weights, long npoint) {
    while (npoint > 0) {
        if ((*rho) > 0.0)
            *weights *= switch_fn(log10(*rho) - log10(rho0), alpha);

        // move on
        npoint --;
        rho++;
        weights++;
    }
}

void multiply_near_mask(double* center, UniformGrid* ugrid, double r0,
    double gamma, double* weights) {

    // Find the ranges for the triple loop
    long ranges_begin[3], ranges_end[3];
    double rcut = r0+gamma;
    ugrid->set_ranges_rcut(center, rcut, ranges_begin, ranges_end);

    // Run triple loop
    Range3Iterator r3i = Range3Iterator(ranges_begin, ranges_end, ugrid->get_shape());
    long j[3], jwrap[3];
    for (long ipoint=r3i.get_npoint()-1; ipoint >= 0; ipoint--) {
        r3i.set_point(ipoint, j, jwrap);
        double d = ugrid->dist_grid_point(center, j);
        // mask if needed
        if (d < rcut) {
            // Add to result
            double* dest = ugrid->get_pointer(weights, jwrap);
            *dest *= switch_fn(r0-d, gamma);
        }
    }

}

void multiply_far_mask(double* centers, long ncenter, UniformGrid* ugrid,
    double r0, double gamma, double* weights) {

    // prepare some variables needed in the loop
    const double rcut = r0 - gamma;
    const Cell* cell = ugrid->get_cell();

    // Run triple loop
    Range3Iterator r3i = Range3Iterator(NULL, ugrid->get_shape(), NULL);
    long j[3];
    for (long ipoint=r3i.get_npoint()-1; ipoint >= 0; ipoint--) {
        r3i.set_point(ipoint, j, NULL);
        double expsum = 0.0;
        for (long icenter=0; icenter<ncenter; icenter++) {
            double delta[3];
            delta[0] = centers[3*icenter];
            delta[1] = centers[3*icenter+1];
            delta[2] = centers[3*icenter+2];
            ugrid->dist_grid_point(delta, j);
            cell->mic(delta);
            expsum += exp(-sqrt(delta[0]*delta[0] + delta[1]*delta[1] + delta[2]*delta[2]));
        }
        const double d = -log(expsum);
        if (d > rcut) {
            double* dest = ugrid->get_pointer(weights, j);
            *dest *= switch_fn(d-r0, gamma);
        }
    }

}
