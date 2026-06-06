import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { FormsModule } from '@angular/forms';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { HomeComponent } from './features/home/home.component';

/** Main app module that connects components, routing, forms, HTTP clients, and interceptors. */
import { SessionComponent } from './features/session/session.component';
import { LoginComponent } from './features/auth/login.component';
import { RegisterComponent } from './features/auth/register.component';
import { ProfileComponent } from './features/profile/profile.component';
import { AuthInterceptor } from './core/auth.interceptor';
import { SessionLauncherComponent } from './features/session/session-launcher/session-launcher.component';

@NgModule({
  declarations: [
    AppComponent,
    HomeComponent,
    SessionComponent,
    LoginComponent,
    RegisterComponent,
    ProfileComponent,
    SessionLauncherComponent
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    AppRoutingModule,
    FormsModule,
    HttpClientModule
  ],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    }
  ],
  bootstrap: [AppComponent]
})
/** Main module class for the Voting App frontend. */
export class AppModule { }
