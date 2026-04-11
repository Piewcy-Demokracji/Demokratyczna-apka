import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { HomeComponent } from './features/home/home.component';
import { LoginComponent } from './features/auth/login.component';
import { RegisterComponent } from './features/auth/register.component';
import { SessionComponent } from './features/session/session.component';
import { ProfileComponent } from './features/profile/profile.component';
import { CreateOptionSetComponent } from './features/profile/create-option-set/create-option-set.component';

const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'session/:token', component: SessionComponent },
  { path: 'profile', component: ProfileComponent },
  { path: 'profile/create-option-set', component: CreateOptionSetComponent },
  { path: 'profile/edit-option-set/:id', component: CreateOptionSetComponent },
  { path: '**', redirectTo: '' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
