import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { TemplateService, Template } from '../../../core/services/template.service';
import { SessionService, SessionCreateResponse } from '../../../core/services/session.service';

@Component({
  selector: 'app-session-launcher',
  templateUrl: './session-launcher.component.html',
  styleUrls: ['./session-launcher.component.css']
})
export class SessionLauncherComponent implements OnInit {
  templateId!: number;
  title = '';
  options: string[] = [];
  durationMinutes = 3;
  votingMode: 'stars' | 'single' = 'stars';
  loading = true;
  launching = false;
  error = '';

  votingModeOptions = [
    {
      value: 'stars' as const,
      label: 'Gwiazdki',
      description: 'Każdą opcję oceniasz osobno w skali 1-5.'
    },
    {
      value: 'single' as const,
      label: 'Jedna opcja',
      description: 'Wybierasz tylko jedną opcję.'
    }
  ];

  presets = [
    { label: '1 min', value: 1 },
    { label: '3 min', value: 3 },
    { label: '5 min', value: 5 },
    { label: '10 min', value: 10 },
  ];
  get filledOptionsCount(): number {
    return this.options.filter(o => o.trim().length > 0).length;
  }

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private templateService: TemplateService,
    private sessionService: SessionService
  ) {}

  ngOnInit(): void {
    this.templateId = Number(this.route.snapshot.paramMap.get('templateId'));
    this.templateService.getTemplate(this.templateId).subscribe({
      next: (t: Template) => {
        this.title = t.title;
        this.options = t.options.map(o => o.text);
        this.loading = false;
      },
      error: () => {
        this.error = 'Nie udało się załadować szablonu.';
        this.loading = false;
      }
    });
  }

  addOption(): void { this.options.push(''); }

  removeOption(index: number): void {
    if (this.options.length > 2) this.options.splice(index, 1);
  }

  trackByIndex(i: number): number { return i; }

  launch(): void {
    const filled = this.options.map(o => o.trim()).filter(o => o.length > 0);
    if (!this.title.trim()) { this.error = 'Tytuł jest wymagany.'; return; }
    if (filled.length < 2) { this.error = 'Wymagane są co najmniej 2 opcje.'; return; }
    if (this.durationMinutes < 1 || this.durationMinutes > 60) {
      this.error = 'Czas musi być między 1 a 60 minut.'; return;
    }

    this.launching = true;
    this.error = '';

    this.sessionService.createSession({
      template_id: this.templateId,
      duration_seconds: this.durationMinutes * 60,
      options: filled,
      voting_mode: this.votingMode
    }).subscribe({
      next: (res: SessionCreateResponse) => this.router.navigate(['/session', res.token]),
      error: () => { this.error = 'Nie udało się utworzyć sesji.'; this.launching = false; }
    });
  }
}