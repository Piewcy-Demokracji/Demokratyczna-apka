import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { SessionService, SessionStatusResponse } from '../../core/services/session.service';

@Component({
  selector: 'app-session',
  templateUrl: './session.component.html',
  styleUrls: ['./session.component.css']
})
export class SessionComponent implements OnInit, OnDestroy {
  sessionCode: string | null = null;
  status: 'Host' | 'Participant' | null = null;
  isHost = false;
  currentUsername: string | null = null;
  sessionEnded = false;
  private pollInterval: any;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private sessionService: SessionService
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(username => {
      this.currentUsername = username;
    });

    const code = this.route.snapshot.paramMap.get('code');
    if (!code) {
      this.router.navigate(['/']);
      return;
    }

    this.sessionCode = code;
    this.loadSession(code);
    this.pollInterval = setInterval(() => this.checkSession(code), 5000);
  }

  ngOnDestroy(): void {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  }

  endSession(): void {
    if (!this.sessionCode) {
      return;
    }

    this.sessionService.endSession(this.sessionCode).subscribe({
      next: () => this.redirectToHome(),
      error: () => this.redirectToHome()
    });
  }

  leaveSession(): void {
    if (!this.sessionCode) {
      return;
    }

    this.sessionService.leaveSession(this.sessionCode).subscribe({
      next: () => this.redirectToHome(),
      error: () => this.redirectToHome()
    });
  }

  private loadSession(code: string): void {
    this.sessionService.getSession(code).subscribe({
      next: response => this.handleSessionResponse(response),
      error: () => this.handleSessionEnded()
    });
  }

  private checkSession(code: string): void {
    this.sessionService.getSession(code).subscribe({
      next: () => {},
      error: () => this.handleSessionEnded()
    });
  }

  private handleSessionResponse(response: SessionStatusResponse): void {
    this.sessionCode = response.code;
    this.status = response.status;
    this.isHost = response.status === 'Host';
  }

  private handleSessionEnded(): void {
    this.sessionEnded = true;
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
    setTimeout(() => this.router.navigate(['/']), 2000);
  }

  private redirectToHome(): void {
    this.router.navigate(['/']);
  }
}
