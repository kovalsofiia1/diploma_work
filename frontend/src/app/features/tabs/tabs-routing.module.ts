import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TabsPage } from './tabs.page';
import { AuthGuard } from '../../core/auth.guard';

const routes: Routes = [
  {
    path: '',
    component: TabsPage,
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'home',
      },
      {
        path: 'home',
        loadChildren: () => import('../home/home.module').then(m => m.HomePageModule),
      },
      {
        path: 'events',
        loadChildren: () => import('../events/events.module').then(m => m.EventsModule),
      },
      {
        path: 'tickets',
        loadChildren: () => import('../booking/booking.module').then(m => m.BookingModule),
      },
      {
        path: 'profile',
        loadChildren: () => import('../profile/profile.module').then(m => m.ProfileModule),
        canActivate: [AuthGuard],
      },
      // Fallback redirects for old paths
      {
        path: 'explore',
        pathMatch: 'full',
        redirectTo: 'events',
      },
      {
        path: 'create',
        pathMatch: 'full',
        redirectTo: 'events/create',
      }
    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class TabsRoutingModule {}

