import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { EventsListPage } from './pages/explore/events-list.page';
import { EventDetailPage } from './pages/detail/event-detail.page';
import { EventCreatePage } from './pages/create/event-create.page';
import { OrganizerCabinetPage } from './pages/organizer-cabinet/organizer-cabinet.page';
import { EventSettingsPage } from './pages/settings/event-settings.page';

const routes: Routes = [
  {
    path: '',
    component: EventsListPage,
  },
  {
    path: 'create',
    component: EventCreatePage,
  },
  {
    path: 'organizer-cabinet',
    component: OrganizerCabinetPage,
  },
  {
    path: 'organizer-cabinet/:uid/settings',
    component: EventSettingsPage,
  },
  {
    path: ':uid',
    component: EventDetailPage,
  },


];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class EventsRoutingModule {}


