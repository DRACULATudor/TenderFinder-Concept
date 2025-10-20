import { Routes } from '@angular/router';
import { TenderDetailedView } from './components/tender-detailed-view/tender-detailed-view';
import { WelcomeComponent } from './components/welcome/welcome.component';
import { TenderSearchComponent } from './components/tender-search/tender-search.component';

export const routes: Routes = [
    {
        path: "",
        redirectTo: "/welcome",
        pathMatch: "full"
    },
    {
        path: "welcome",
        component: WelcomeComponent
    },
    {
        path: "search",
        component: TenderSearchComponent
    },
    {
        path: "tender/detailed-view",
        component: TenderDetailedView,
    },
    {
        path: "tender/:id/:pubId",
        component: TenderDetailedView,
    },
    {
        path: "tender/:id",
        component: TenderDetailedView,
    }
];
