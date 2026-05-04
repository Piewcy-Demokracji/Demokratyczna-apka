import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { TemplateService, Template } from '../../../core/services/template.service';
import { SessionService, SessionCreateResponse } from '../../../core/services/session.service';
import { HttpClient } from '@angular/common/http';

interface LauncherOption {
  text: string;
  image_filename: string | null;
  uploading: boolean;
  uploadError: string | null;
}

@Component({
  selector: 'app-session-launcher',
  templateUrl: './session-launcher.component.html',
  styleUrls: ['./session-launcher.component.css']
})

export class SessionLauncherComponent implements OnInit {
  templateId!: number;
  title = '';
  options: LauncherOption[] = [];
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
    return this.options.filter(o => o.text.trim().length > 0).length;
  }

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private templateService: TemplateService,
    private sessionService: SessionService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.templateId = Number(this.route.snapshot.paramMap.get('templateId'));
    this.templateService.getTemplate(this.templateId).subscribe({
      next: (t: Template) => {
        this.title = t.title;
        this.options = t.options.map(o => ({
          text: o.text,
          image_filename: (o as any).image_filename || null,
          uploading: false,
          uploadError: null
        }));
        this.loading = false;
      },
      error: () => {
        this.error = 'Nie udało się załadować szablonu.';
        this.loading = false;
      }
    });
  }

  addOption(): void { this.options.push({ text: '', image_filename: null, uploading: false, uploadError: null }); }

  removeOption(index: number): void {
    if (this.options.length > 2) this.options.splice(index, 1);
  }

  trackByIndex(i: number): number { return i; }

  launch(): void {
    const filled = this.options.filter(o => o.text.trim().length > 0).map(o => ({ text: o.text.trim(), image_filename: o.image_filename }));
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
      options: filled.map(o => o.text),
      options_with_images: filled,
      voting_mode: this.votingMode
    }).subscribe({
      next: (res: SessionCreateResponse) => this.router.navigate(['/session', res.token]),
      error: () => { this.error = 'Nie udało się utworzyć sesji.'; this.launching = false; }
    });
  }

  getImageUrl(filename: string | null): string | null {
    return filename ? `http://localhost:8000/api/upload/${filename}` : null;
  }

  onFileSelected(event: Event, index: number): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  this.options[index].uploading = true;
  this.options[index].uploadError = null;

  const formData = new FormData();
  formData.append('file', file, file.name);

  this.http.post<any>('http://localhost:8000/api/upload/', formData).subscribe({
    next: (response) => {
      this.options[index].image_filename = response.filename;
      this.options[index].uploading = false;
    },
    error: (err) => {
      this.options[index].uploadError = err?.error?.detail || 'Upload nie powiódł się';
      this.options[index].uploading = false;
    }
  });
  }
}