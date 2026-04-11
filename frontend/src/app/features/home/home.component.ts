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

  updateJoinCode(value: string): void {
    this.joinCode = value.toUpperCase();
  }

  enterSession(): void {
    if (!this.joinCode) {
      this.errorMessage = 'Enter your session code.';
      return;
    }

    this.sessionService.joinSession(this.joinCode.trim()).subscribe({
      next: response => {
        this.errorMessage = null;
        this.router.navigate(['/session', response.token]);
      },
      error: () => {
        this.errorMessage = 'Invalid session code.';
        this.joinCode = '';
      }
    });
  }
}
