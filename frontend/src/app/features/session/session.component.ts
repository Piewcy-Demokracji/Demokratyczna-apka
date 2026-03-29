import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { SessionService, SessionStatusResponse } from '../../core/services/session.service';

interface PollOption {
  id: number;
  name: string;
  rating_count: number;
  total_rating: number;
  userRating?: number;
  avg_rating?: number;
}

interface Poll {
  id: number;
  title: string;
  duration_seconds: number;
  start_time: number;
  options: PollOption[];
}

@Component({
  selector: 'app-session',
  templateUrl: './session.component.html',
  styleUrls: ['./session.component.css']
})
export class SessionComponent implements OnInit, OnDestroy {
  sessionToken: string | null = null;
  sessionPassword: string | null = null;
  status: 'Host' | 'Participant' | null = null;
  isHost = false;
  currentUsername: string | null = null;
  sessionEnded = false;

  poll: Poll | null = null;
  timeLeft = 0;
  timerId: any = null;
  isComplete = false;
  summaryOptions: PollOption[] = [];
  message = '';

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

    const token = this.route.snapshot.paramMap.get('token');
    if (!token) {
      this.router.navigate(['/']);
      return;
    }

    this.sessionToken = token;
    this.loadSession(token);
    this.pollInterval = setInterval(() => this.checkSession(token), 5000);
  }

  ngOnDestroy(): void {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  }

  endSession(): void {
    if (!this.sessionToken) {
      return;
    }

    this.sessionService.endSession(this.sessionToken).subscribe({
      next: () => this.redirectToHome(),
      error: () => this.redirectToHome()
    });
  }

  leaveSession(): void {
    if (!this.sessionToken) {
      return;
    }

    this.sessionService.leaveSession(this.sessionToken).subscribe({
      next: () => this.redirectToHome(),
      error: () => this.redirectToHome()
    });
  }

  private loadSession(token: string): void {
    this.sessionService.getSession(token).subscribe({
      next: response => {
        this.handleSessionResponse(response);
        if (response.poll) {
          this.poll = {
            ...response.poll,
            options: response.poll.options.map(o => ({ ...o, userRating: 0 }))
          };
          this.updateTimeFromPoll();
          this.startCountdown();
        }
      },
      error: () => this.handleSessionEnded()
    });
  }

  private checkSession(token: string): void {
    if (!this.sessionToken || this.sessionEnded || this.isComplete) {
      return;
    }

    this.sessionService.getSession(token).subscribe({
      next: response => {
        if (response.poll) {
          this.poll = {
            ...response.poll,
            options: response.poll.options.map(o => ({
              ...o,
              userRating: 0
            }))
          };
          this.updateTimeFromPoll();
          if (this.timeLeft <= 0 && !this.isComplete) {
            this.finishPolling();
          }
        }
      },
      error: () => this.handleSessionEnded()
    });
  }

  private handleSessionResponse(response: SessionStatusResponse): void {
    this.sessionPassword = response.code ?? null;
    this.status = response.status;
    this.isHost = response.status === 'Host';
  }

  private handleSessionEnded(): void {
    this.sessionEnded = true;
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    setTimeout(() => this.router.navigate(['/']), 2000);
  }

  private redirectToHome(): void {
    this.router.navigate(['/']);
  }

  private updateTimeFromPoll(): void {
    if (!this.poll || !this.poll.start_time) {
      this.timeLeft = 0;
      return;
    }

    const now = Math.floor(Date.now() / 1000);
    const elapsed = now - this.poll.start_time;
    this.timeLeft = Math.max(this.poll.duration_seconds - elapsed, 0);
  }

  private startCountdown(): void {
    if (this.timerId) {
      clearInterval(this.timerId);
    }

    this.isComplete = false;

    this.timerId = setInterval(() => {
      this.updateTimeFromPoll();
      if (this.timeLeft <= 0) {
        this.finishPolling();
      }
    }, 1000);
  }

  private finishPolling(): void {
    this.isComplete = true;
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }

    if (!this.poll) {
      return;
    }

    this.summaryOptions = this.poll.options
      .map(option => {
        const ratingCount = option.rating_count || 0;
        const totalRating = option.total_rating || 0;
        const avg = ratingCount > 0 ? totalRating / ratingCount : 0;
        return {
          ...option,
          avg_rating: avg,
        } as PollOption & { avg_rating: number };
      })
      .sort((a, b) => ((b as any).avg_rating || 0) - ((a as any).avg_rating || 0));
  }

  formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  goHome(): void {
    this.router.navigate(['/']);
  }

  rateOption(option: PollOption, star: number): void {
    if (!this.poll || this.isComplete || !this.sessionToken) {
      return;
    }

    option.userRating = star;

    this.sessionService.vote(this.sessionToken, option.id, star).subscribe({
      next: () => {
        this.checkSession(this.sessionToken!);
      },
      error: () => {
        this.message = 'Failed to record vote. Please try again.';
      }
    });
  }

  getStarClass(option: PollOption, index: number): string {
    if ((option.userRating || 0) >= index) {
      return 'star active';
    }
    return 'star';
  }

  solidifySummary(): void {
    if (!this.poll) {
      return;
    }
    this.finishPolling();
  }
}

