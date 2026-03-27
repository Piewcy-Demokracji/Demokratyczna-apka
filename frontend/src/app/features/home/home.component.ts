import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { SessionService } from '../../core/services/session.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {
  isLoggedIn = false;
  currentUsername: string | null = null;
  joinCode = '';
  errorMessage: string | null = null;

  constructor(
    private authService: AuthService,
    private sessionService: SessionService,
    private router: Router
  ) {
    this.authService.currentUser$.subscribe(username => {
      this.currentUsername = username;
      this.isLoggedIn = !!username;
    });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/']);
  }

  createSession(): void {
    if (!this.isLoggedIn) {
      this.errorMessage = 'You must be logged in to create a session.';
      return;
    }

    this.sessionService.createSession().subscribe({
      next: response => {
        this.errorMessage = null;
        this.router.navigate(['/session', response.code]);
      },
      error: () => {
        this.errorMessage = 'Unable to create session. Please try again.';
      }
    });
  }

  enterSession(): void {
    if (!this.joinCode) {
      this.errorMessage = 'Enter a valid 4-digit session code.';
      return;
    }

    this.sessionService.joinSession(this.joinCode).subscribe({
      next: () => {
        this.errorMessage = null;
        this.router.navigate(['/session', this.joinCode]);
      },
      error: () => {
        this.errorMessage = 'Invalid session code or you are not part of this session.';
        this.joinCode = '';
      }
    });
  }
}
