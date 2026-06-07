import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { TemplateService, Template } from '../../../core/services/template.service';
import { SessionService, SessionCreateResponse, SessionOptionInput } from '../../../core/services/session.service';
import { UploadService } from '../../../core/services/upload.service';

interface OptionDraft {
  text: string;
  image_path: string | null;
  uploading?: boolean;
}

@Component({
  selector: 'app-session-launcher',
  templateUrl: './session-launcher.component.html',
  styleUrls: ['./session-launcher.component.css']
})
/** Component for launching a new session from a chosen template and customizing voting parameters. */
export class SessionLauncherComponent implements OnInit, OnDestroy {
  templateId!: number;
  title = '';
  options: OptionDraft[] = [];
  durationMinutes = 3;
  votingMode: 'stars' | 'single' = 'stars';
  loading = true;
  launching = false;
  error = '';
  uploadError = '';

  // Paths loaded from template on init; never auto-deleted (template still owns them)
  private originalPaths = new Set<string>();
  private launched = false;

  votingModeOptions = [
    { value: 'stars' as const, label: 'Gwiazdki', description: 'Każdą opcję oceniasz osobno w skali 1-5.' },
    { value: 'single' as const, label: 'Jedna opcja', description: 'Wybierasz tylko jedną opcję.' }
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
    private uploadService: UploadService,
  ) {}

  ngOnInit(): void {
    this.templateId = Number(this.route.snapshot.paramMap.get('templateId'));
    this.templateService.getTemplate(this.templateId).subscribe({
      next: (t: Template) => {
        this.title = t.title;
        this.options = t.options.map(o => ({
          text: o.text,
          image_path: o.image_path ?? null,
        }));
        this.originalPaths = new Set(
          t.options
            .map(o => o.image_path)
            .filter((p): p is string => !!p)
        );
        this.loading = false;
      },
      error: () => {
        this.error = 'Nie udało się załadować szablonu.';
        this.loading = false;
      }
    });
  }

  ngOnDestroy(): void {
    if (this.launched) {
      return;
    }
    this.options.forEach(opt => {
      if (opt.image_path && !this.originalPaths.has(opt.image_path)) {
        this.uploadService.deleteImage(opt.image_path).subscribe({ error: () => {} });
      }
    });
  }

  addOption(): void {
    this.options.push({ text: '', image_path: null });
  }

  removeOption(index: number): void {
    if (this.options.length <= 2) {
      return;
    }
    const path = this.options[index].image_path;
    if (path && !this.originalPaths.has(path)) {
      this.uploadService.deleteImage(path).subscribe({ error: () => {} });
    }
    this.options.splice(index, 1);
  }

  trackByIndex(i: number): number { return i; }

  getImageUrl(path: string | null): string | null {
    return this.uploadService.getImageUrl(path);
  }

  onImageSelected(event: Event, index: number): void {
    this.uploadError = '';
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) { return; }
    const file = input.files[0];
    const validationError = this.uploadService.validateFile(file);
    if (validationError) {
      this.uploadError = validationError;
      input.value = '';
      return;
    }

    this.options[index].uploading = true;
    this.uploadService.uploadImage(file).subscribe({
      next: (response: { image_path: string }) => {
        this.options[index].image_path = response.image_path;
        this.options[index].uploading = false;
        input.value = '';
      },
      error: (err: unknown) => {
        console.error('Upload error:', err);
        this.uploadError = 'Nie udało się wgrać obrazka.';
        this.options[index].uploading = false;
        input.value = '';
      }
    });
  }

  removeImage(index: number): void {
    const path = this.options[index].image_path;
    if (path && !this.originalPaths.has(path)) {
      this.uploadService.deleteImage(path).subscribe({ error: () => {} });
    }
    this.options[index].image_path = null;
  }

  launch(): void {
    const filled = this.options
      .filter(o => o.text.trim().length > 0)
      .map(o => ({ text: o.text.trim(), image_path: o.image_path } as SessionOptionInput));

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
      voting_mode: this.votingMode,
    }).subscribe({
      next: (res: SessionCreateResponse) => {
        this.launched = true;
        this.router.navigate(['/session', res.token]);
      },
      error: (err: unknown) => {
        console.error('Launch error:', err);
        this.error = 'Nie udało się utworzyć sesji.';
        this.launching = false;
      }
    });
  }
}