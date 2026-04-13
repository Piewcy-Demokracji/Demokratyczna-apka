import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { HomeComponent } from './features/home/home.component';
import { LoginComponent } from './features/auth/login.component';
import { RegisterComponent } from './features/auth/register.component';
import { SessionComponent } from './features/session/session.component';
import { ProfileComponent } from './features/profile/profile.component';
import { CreateOptionSetComponent } from './features/profile/create-option-set/create-option-set.component';
import { AdminOptionSetsComponent } from './features/admin/admin-option-sets/admin-option-sets.component';
import { AdminOptionSetReviewComponent } from './features/admin/admin-option-set-review/admin-option-set-review.component';
import { SessionLauncherComponent } from './features/session/session-launcher/session-launcher.component';

const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'session/launch/:templateId', component: SessionLauncherComponent },
  { path: 'session/:token', component: SessionComponent },
  { path: 'profile', component: ProfileComponent },
  { path: 'profile/create-option-set', component: CreateOptionSetComponent },
  { path: 'profile/edit-option-set/:id', component: CreateOptionSetComponent },
  { path: 'admin/option-sets', component: AdminOptionSetsComponent },
  { path: 'admin/option-sets/:id', component: AdminOptionSetReviewComponent },
  { path: '**', redirectTo: '' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
