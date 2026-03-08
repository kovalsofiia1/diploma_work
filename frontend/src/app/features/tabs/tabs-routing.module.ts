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
        path: 'explore',
        loadChildren: () =>
          import('../events/explore/explore.module').then((m) => m.EventsExploreModule),
      },
      {
        path: 'create',
        loadChildren: () =>
          import('../events/create/create.module').then((m) => m.EventsCreateModule),
      },
      {
        path: 'tickets',
        loadChildren: () => import('../booking/booking.module').then(m => m.BookingModule),
      },
      {
        path: 'events/create',
        pathMatch: 'full',
        redirectTo: 'create',
      },
      {
        path: 'events/:uid',
        redirectTo: 'explore/:uid',
      },
      {
        path: 'events',
        pathMatch: 'full',
        redirectTo: 'explore',
      },
      {
        path: 'profile',
        loadChildren: () => import('../profile/profile.module').then(m => m.ProfileModule),
        canActivate: [AuthGuard],
      },

    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class TabsRoutingModule {}

