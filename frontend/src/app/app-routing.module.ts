import { NgModule } from '@angular/core';
import { PreloadAllModules, RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.module').then(m => m.AuthModule)
  },
  {
    path: 'tabs',
    loadChildren: () => import('./features/tabs/tabs.module').then(m => m.TabsModule)
  },
  { path: '', pathMatch: 'full', redirectTo: 'tabs' },
  { path: '**', redirectTo: 'tabs' },
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, { preloadingStrategy: PreloadAllModules })
  ],
  exports: [RouterModule]
})
export class AppRoutingModule { }
