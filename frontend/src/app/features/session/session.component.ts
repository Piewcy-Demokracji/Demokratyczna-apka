import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { SessionService, SessionStatusResponse } from '../../core/services/session.service';
import { UploadService } from '../../core/services/upload.service';

interface PollOption {
  id: number;
  name: string;
  rating_count: number;
  total_rating: number;
  userRating?: number;
  user_rating?: number;
  avg_rating?: number;
  image_path?: string | null;
}

interface Poll {
  id: number;
  title: string;
  duration_seconds: number;
  start_time: number;
  voting_mode: 'stars' | 'single';
  options: PollOption[];
}

@Component({
  selector: 'app-session',
  templateUrl: './session.component.html',
  styleUrls: ['./session.component.css']
})
/** Component for displaying session state, poll voting UI, and session lifecycle controls. */
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
  image_base64: string | null=null;

  private pollInterval: any;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private sessionService: SessionService,
    private uploadService: UploadService,
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(username => {
      this.currentUsername = username;
    });

    this.route.paramMap.subscribe(params => {
      const token = params.get('token');
      if (!token) {
        this.router.navigate(['/']);
        return;
      }

      this.resetSessionState();
      this.sessionToken = token;
      this.loadSession(token);
      this.pollInterval = setInterval(() => this.checkSession(token), 5000);
    });
  }

  ngOnDestroy(): void {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  }

  getImageUrl(path: string | null | undefined): string | null {
    return this.uploadService.getImageUrl(path);
  }

  endSession(): void {
    if (!this.sessionToken) { return; }
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
    this.isComplete = false;
    this.summaryOptions = [];
    this.sessionEnded = false;
    this.message = '';

    this.sessionService.getSession(token).subscribe({
      next: response => {
        this.handleSessionResponse(response);
        if (response.poll) {
          this.poll = {
            ...response.poll,
            options: this.mapPollOptions(response.poll.options)
          };
          this.updateTimeFromPoll();
          if (this.timeLeft <= 0 || this.sessionEnded) {
            this.finishPolling();
          } else {
            this.startCountdown();
          }
        }
      },
      error: () => this.handleSessionEnded()
    });
  }

  private checkSession(token: string): void {
    if (!this.sessionToken || this.sessionEnded || this.isComplete) { return; }

    this.sessionService.getSession(token).subscribe({
      next: response => {
        this.handleSessionResponse(response);
        if (response.poll) {
          this.poll = {
            ...response.poll,
            options: this.mapPollOptions(response.poll.options)
          };
          this.updateTimeFromPoll();
          if ((this.timeLeft <= 0 || this.sessionEnded) && !this.isComplete) {
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
    this.sessionEnded = (response.session_status ?? 'ACTIVE') !== 'ACTIVE';
    this.image_base64 = response.image_base64 ?? null;
  }

  private handleSessionEnded(): void {
    this.sessionEnded = true;
    if (this.pollInterval) { clearInterval(this.pollInterval); }
    if (this.timerId) { clearInterval(this.timerId); this.timerId = null; }
    setTimeout(() => this.router.navigate(['/']), 2000);
  }

  private redirectToHome(): void {
    this.router.navigate(['/']);
  }

  private resetSessionState(): void {
    if (this.pollInterval) { clearInterval(this.pollInterval); this.pollInterval = null; }
    if (this.timerId) { clearInterval(this.timerId); this.timerId = null; }
    this.sessionEnded = false;
    this.poll = null;
    this.timeLeft = 0;
    this.isComplete = false;
    this.summaryOptions = [];
    this.message = '';
    this.status = null;
    this.isHost = false;
    this.sessionPassword = null;
    this.image_base64 = null;
  }

  private updateTimeFromPoll(): void {
    if (!this.poll) { this.timeLeft = 0; return; }
    const now = Math.floor(Date.now() / 1000);
    const elapsed = now - this.poll.start_time;
    this.timeLeft = Math.max(this.poll.duration_seconds - elapsed, 0);
  }

  private mapPollOptions(options: PollOption[]): PollOption[] {
    const existingRatings = new Map<number, number>();

    if (this.poll?.options) {
      this.poll.options.forEach(option => {
        if (option.userRating) {
          existingRatings.set(option.id, option.userRating);
        }
      });
    }

    return options.map(option => ({
      ...option,
      userRating: option.user_rating ?? option.userRating ?? existingRatings.get(option.id) ?? 0,
      image_path: option.image_path ?? null,
    }));
  }

  private startCountdown(): void {
    if (this.timerId) { clearInterval(this.timerId); }
    this.isComplete = false;
    this.timerId = setInterval(() => {
      this.updateTimeFromPoll();
      if (this.timeLeft <= 0) { this.finishPolling(); }
    }, 1000);
  }

  private finishPolling(): void {
    this.isComplete = true;
    if (this.timerId) { clearInterval(this.timerId); this.timerId = null; }
    if (!this.poll) { return; }

    const totalVotes = this.isSingleChoiceMode()
      ? this.poll.options.reduce((sum, option) => sum + (option.rating_count || 0), 0)
      : 0;

    this.summaryOptions = this.poll.options
      .map(option => {
        const ratingCount = option.rating_count || 0;
        const totalRating = option.total_rating || 0;
        const avg = this.isSingleChoiceMode()
          ? (totalVotes > 0 ? Math.round((ratingCount / totalVotes) * 100) : 0)
          : (ratingCount > 0 ? totalRating / ratingCount : 0);
        return { ...option, avg_rating: avg };
      })
      .sort((a, b) => ((b as any).avg_rating || 0) - ((a as any).avg_rating || 0));
  }

  isSingleChoiceMode(): boolean {
    return this.poll?.voting_mode === 'single';
  }

  getSummaryPrimaryLabel(): string {
    return this.isSingleChoiceMode() ? 'Percentage' : 'Average';
  }

  getSummaryPrimaryValue(option: PollOption): string {
    const score = option.avg_rating || 0;
    return this.isSingleChoiceMode() ? `${Math.round(score)}%` : score.toFixed(1);
  }

  formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  endPollEarly(): void {
    if (!this.isHost || !this.sessionToken) { return; }
    this.sessionService.endPollEarly(this.sessionToken).subscribe({
      next: response => {
        this.handleSessionResponse(response);
        if (response.poll) {
          this.poll = { ...response.poll, options: this.mapPollOptions(response.poll.options) };
        }
        this.updateTimeFromPoll();
        this.finishPolling();
      },
      error: () => { this.timeLeft = 0; this.finishPolling(); }
    });
  }

  goHome(): void {
    this.router.navigate(['/']);
  }

  rateOption(option: PollOption, star: number): void {
    if (!this.poll || this.isComplete || !this.sessionToken) { return; }

    if (this.isSingleChoiceMode()) {
      this.poll.options.forEach(candidate => {
        candidate.userRating = candidate.id === option.id ? 1 : 0;
      });
    } else {
      option.userRating = star;
    }

    this.sessionService.vote(this.sessionToken, option.id, this.isSingleChoiceMode() ? 1 : star).subscribe({
      next: () => { this.checkSession(this.sessionToken!); },
      error: () => { this.message = 'Failed to record vote. Please try again.'; }
    });
  }

  getStarClass(option: PollOption, index: number): string {
    return (option.userRating ?? 0) >= index ? 'star active' : 'star';
  }

  solidifySummary(): void {
    if (this.poll) { this.finishPolling(); }
  }

  downloadResults(): void {
    if (!this.image_base64) { return; }
    const pollTitle = this.poll?.title || 'results';
    const sanitizedTitle = pollTitle.replace(/[\/\\:*?"<>|]/g, '_');
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${this.image_base64}`;
    link.download = `${sanitizedTitle}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}